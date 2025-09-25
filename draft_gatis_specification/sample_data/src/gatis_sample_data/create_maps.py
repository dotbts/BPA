import json
import math
from html import escape
import folium
from folium.features import GeoJson, GeoJsonTooltip
import pandas as pd
import matplotlib.cm as cm
import matplotlib.colors as mcolors

from pyprojroot import here

def add_to_json(map_dict):
    
    maps_path = here("draft_gatis_specification/sample_data/maps")
    
    map_dict['path'] = maps_path / f"{map_dict.get('key')}.html"
    
    maps_json_fp = maps_path / "maps.json"
    
    if maps_json_fp.exists():
        with maps_json_fp.open('r') as fh:
            maps_json = json.load(fh)
    else:
        maps_json = []

    # check for existing
    existing = [(idx,x) for idx, x in enumerate(maps_json) if x.get('key') == map_dict.get('key')]
    if len(existing) == 0:
        maps_json.append(map_dict)
    else:
        maps_json[existing[0][0]] = map_dict

    with maps_json_fp.open('w') as fh:
        json.dump(maps_json,fh,indent=4)

    return maps_json

def display_layers(
    lines_gdf=None,
    points_gdf=None,
    polygons_gdf=None,
    zoom_start=17,
    display_cols=None,
    points_radius=5,
    edge_categories=None,
    node_categories=None,
    polygon_categories=None,            # NEW: categorical column for polygons
    cmap_name="Set1",
    default_edge_color="#3388ff",
    default_node_fill="#0FDCBA",
    default_node_outline="#000000",
    default_polygon_fill="#FFD966",     # NEW: default polygon fill
    default_polygon_outline="#666666",  # NEW: default polygon outline
    basemap=True  # toggle basemap on/off
):
    """
    Create a folium.Map with three FeatureGroups: "Lines", "Points", and "Polygons".
    Optionally color lines/points/polygons by categorical columns (edge_categories / node_categories / polygon_categories)
    using a matplotlib categorical colormap.
    Adds on-map legends for edge_categories, node_categories, and polygon_categories when provided.
    If multiple legends are present, they are placed horizontally next to each other (edge -> node -> polygon).
    """
    def make_tooltip_html(props, display_cols_local):
        rows = []
        for k in display_cols_local:
            if k not in props:
                continue
            v = props[k]
            # Skip null-like values
            if v is None:
                continue
            if pd.isna(v):
                continue
            if isinstance(v, str) and v.strip() == "":
                continue
            rows.append(
                f"<tr><th style='text-align:left;padding-right:8px'>{escape(str(k))}</th>"
                f"<td>{escape(str(v))}</td></tr>"
            )
        if not rows:
            return ""
        return "<table style='border-collapse:collapse'>" + "".join(rows) + "</table>"

    # ensure display_cols is list if provided
    if display_cols is not None:
        display_cols = list(display_cols)

    # prepare color maps for edges, nodes, and polygons if requested
    edge_color_map = None
    node_color_map = None
    polygon_color_map = None

    # helper to build a mapping from category value -> hex color
    def build_category_color_map(values, cmap_name):
        # unique values preserving order
        unique_vals = []
        seen = set()
        for v in values:
            if pd.isna(v):
                continue
            if v not in seen:
                seen.add(v)
                unique_vals.append(v)
        n = max(len(unique_vals), 1)
        cmap = cm.get_cmap(cmap_name, n)
        color_map = {}
        for i, val in enumerate(unique_vals):
            rgba = cmap(i)
            color_map[val] = mcolors.to_hex(rgba)
        return color_map

    if lines_gdf is not None and edge_categories is not None:
        if edge_categories not in lines_gdf.columns:
            raise ValueError(f"edge_categories '{edge_categories}' not found in lines_gdf columns")
        edge_color_map = build_category_color_map(lines_gdf[edge_categories].tolist(), cmap_name)

    if points_gdf is not None and node_categories is not None:
        if node_categories not in points_gdf.columns:
            raise ValueError(f"node_categories '{node_categories}' not found in points_gdf columns")
        node_color_map = build_category_color_map(points_gdf[node_categories].tolist(), cmap_name)

    if polygons_gdf is not None and polygon_categories is not None:
        if polygon_categories not in polygons_gdf.columns:
            raise ValueError(f"polygon_categories '{polygon_categories}' not found in polygons_gdf columns")
        polygon_color_map = build_category_color_map(polygons_gdf[polygon_categories].tolist(), cmap_name)

    # Determine map center / bounds
    if lines_gdf is not None and not lines_gdf.empty:
        minx, miny, maxx, maxy = lines_gdf.total_bounds
    elif points_gdf is not None and not points_gdf.empty:
        minx, miny, maxx, maxy = points_gdf.total_bounds
    elif polygons_gdf is not None and not polygons_gdf.empty:
        minx, miny, maxx, maxy = polygons_gdf.total_bounds
    else:
        # fallback to world view
        minx, miny, maxx, maxy = -180.0, -90.0, 180.0, 90.0

    m = folium.Map(location=[(miny + maxy) / 2, (minx + maxx) / 2], zoom_start=zoom_start, tiles=None)

    # --------------------
    # ADD BASEMAPS (optional)
    # --------------------
    if basemap:
        folium.TileLayer(
            "",
            name='None', attr="None", control=True,
            max_zoom=25, max_native_zoom=18, show=True
        ).add_to(m)
        folium.TileLayer(
            "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            name='OpenStreetMap', attr="OpenStreetMap Contributors", control=True,
            max_zoom=25, max_native_zoom=18, show=True
        ).add_to(m)
        folium.TileLayer(
            "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
            name='Google', attr="Google Satellite", control=True,
            max_zoom=25, max_native_zoom=21, show=False
        ).add_to(m)

    # --------------------
    # POLYGONS FEATURE GROUP (NEW)
    # --------------------
    if polygons_gdf is not None:
        polygons_fg = folium.FeatureGroup(name="GATIS Zones", show=True)
        if not polygons_gdf.empty:
            # Prepare geojson dict so we can inject tooltip HTML into properties
            polys_geojson = json.loads(polygons_gdf.to_json())
            # per-feature tooltip HTML
            for feat in polys_geojson["features"]:
                props = feat.setdefault("properties", {})
                cols = display_cols if display_cols is not None else list(polygons_gdf.columns)
                props["_tooltip_html"] = make_tooltip_html(props, cols)

            # style function for polygons (uses polygon_color_map when provided)
            def _poly_style(feature):
                props = feature.get("properties", {})
                fill_color = default_polygon_fill
                outline = default_polygon_outline
                if polygon_color_map is not None:
                    cat = props.get(polygon_categories, None)
                    if cat in polygon_color_map:
                        fill_color = polygon_color_map[cat]
                return {
                    "color": outline,
                    "weight": 1.5,
                    "opacity": 0.9,
                    "fillColor": fill_color,
                    "fillOpacity": 0.6,
                }

            tooltip = GeoJsonTooltip(
                fields=["_tooltip_html"],
                aliases=[""],
                labels=False,
                sticky=True,
                parse_html=True,
                localize=False,
                style=("background-color: white; padding: 4px; border-radius: 3px;")
            )
            GeoJson(
                polys_geojson,
                name="polygons_geojson",
                tooltip=tooltip,
                style_function=_poly_style,
            ).add_to(polygons_fg)
        polygons_fg.add_to(m)

    # --------------------
    # LINES FEATURE GROUP
    # --------------------
    if lines_gdf is not None:
        lines_fg = folium.FeatureGroup(name="GATIS Edges", show=True)
        if not lines_gdf.empty:
            # Prepare geojson dict so we can inject tooltip HTML into properties
            lines_geojson = json.loads(lines_gdf.to_json())
            # per-feature tooltip HTML
            for feat in lines_geojson["features"]:
                props = feat.setdefault("properties", {})
                cols = display_cols if display_cols is not None else list(lines_gdf.columns)
                props["_tooltip_html"] = make_tooltip_html(props, cols)
            # style function for lines (uses edge_color_map when provided)
            def _line_style(feature):
                props = feature.get("properties", {})
                color = default_edge_color
                if edge_color_map is not None:
                    cat = props.get(edge_categories, None)
                    if cat in edge_color_map:
                        color = edge_color_map[cat]
                return {
                    "color": color,
                    "weight": 3,
                    "opacity": 0.9,
                }
            tooltip = GeoJsonTooltip(
                fields=["_tooltip_html"],
                aliases=[""],
                labels=False,
                sticky=True,
                parse_html=True,
                localize=False,
                style=("background-color: white; padding: 4px; border-radius: 3px;")
            )
            GeoJson(
                lines_geojson,
                name="lines_geojson",
                tooltip=tooltip,
                style_function=_line_style,
            ).add_to(lines_fg)
        lines_fg.add_to(m)

    # --------------------
    # POINTS FEATURE GROUP
    # --------------------
    if points_gdf is not None:
        points_fg = folium.FeatureGroup(name="GATIS Nodes", show=True)
        if not points_gdf.empty:
            # We'll iterate rows and add CircleMarkers so we can style outlines etc.
            for _, row in points_gdf.iterrows():
                geom = row.geometry
                if geom is None or geom.is_empty:
                    continue
                cols = display_cols if display_cols is not None else list(points_gdf.columns)
                props = {c: row[c] for c in cols if c in row.index}
                html = make_tooltip_html(props, cols)
                tooltip = folium.Tooltip(html, sticky=True, parse_html=True) if html else None
                # determine fill color based on node_categories if provided
                fill_color = default_node_fill
                if node_color_map is not None:
                    cat = row.get(node_categories, None)
                    if pd.isna(cat):
                        cat = None
                    if cat in node_color_map:
                        fill_color = node_color_map[cat]
                folium.CircleMarker(
                    location=[geom.y, geom.x],
                    radius=points_radius,
                    color=default_node_outline,   # outline color
                    weight=1.25,                  # outline width
                    fill=True,
                    fill_color=fill_color,
                    fill_opacity=0.9,
                    tooltip=tooltip,
                ).add_to(points_fg)
        points_fg.add_to(m)

    # --------------------
    # LEGENDS (if categoricals provided)
    # --------------------
    def legend_html(title, color_map, left_px=10, bottom_px=20, css_class="legend"):
        """
        Build a simple HTML legend block positioned `left_px` from the left and `bottom_px` from the bottom.
        Returns (html_string, estimated_width_px, estimated_height_px).
        """
        if not color_map:
            return "", 0, 0
        items_html = []
        # approximate width per label; used only to estimate horizontal offset
        longest_label_chars = 0
        for label, color in color_map.items():
            label_text = escape(str(label))
            items_html.append(
                f"<li style='margin-bottom:4px; white-space:nowrap;'><span style='display:inline-block;width:12px;height:12px;"
                f"background:{color};margin-right:6px;vertical-align:middle; border:1px solid #000;'></span>"
                f"{label_text}</li>"
            )
            longest_label_chars = max(longest_label_chars, len(label_text))
        # estimate sizes (simple heuristic)
        char_width_px = 7  # approximate average char pixel width
        label_part_width = longest_label_chars * char_width_px
        color_swatch_and_padding = 12 + 6 + 10  # swatch + margin + inner padding
        est_width = color_swatch_and_padding + label_part_width + 20  # extra padding
        item_count = len(color_map)
        est_height = 14 + item_count * 20  # estimate height
        html = f"""
        <div class="{css_class}-container" style="
            position: absolute;
            bottom: {bottom_px}px;
            left: {left_px}px;
            background: rgba(255,255,255,0.95);
            padding: 8px 10px;
            border: 1px solid #bbb;
            border-radius: 6px;
            font-family: system-ui, -apple-system, Segoe UI, Roboto;
            font-size: 12px;
            z-index: 9999;
            max-height: 200px;
            overflow:auto;
            white-space: nowrap;
        ">
            <strong>{escape(title)}</strong>
            <ul style="list-style: none; margin: 6px 0 0 0; padding: 0;">
                {''.join(items_html)}
            </ul>
        </div>
        """
        return html, est_width, est_height

    # Place legends left-to-right: edge -> node -> polygon
    legend_left = 10
    gap_px = 12
    total_legend_width = 0

    if edge_color_map is not None:
        edge_html, edge_legend_width, _ = legend_html("Edge type", edge_color_map, left_px=legend_left, bottom_px=20, css_class="edge-legend")
        m.get_root().html.add_child(folium.Element(edge_html))
        total_legend_width = edge_legend_width
        legend_left += edge_legend_width + gap_px

    if node_color_map is not None:
        node_html, node_legend_width, _ = legend_html("Node type", node_color_map, left_px=legend_left, bottom_px=20, css_class="node-legend")
        m.get_root().html.add_child(folium.Element(node_html))
        total_legend_width += node_legend_width
        legend_left += node_legend_width + gap_px

    if polygon_color_map is not None:
        poly_html, poly_legend_width, _ = legend_html("Polygon type", polygon_color_map, left_px=legend_left, bottom_px=20, css_class="poly-legend")
        m.get_root().html.add_child(folium.Element(poly_html))
        total_legend_width += poly_legend_width
        legend_left += poly_legend_width + gap_px

    # --------------------
    # LAYER CONTROL
    # --------------------
    folium.LayerControl(collapsed=False).add_to(m)

    # Expose color maps for external use if needed
    m._edge_color_map = edge_color_map
    m._node_color_map = node_color_map
    m._polygon_color_map = polygon_color_map

    return m