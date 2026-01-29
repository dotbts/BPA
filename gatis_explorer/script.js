////////////////////////////////////////////////////////////////////////////////
// To-do ///////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////

/*
- Generalize the checkbox function
- Move the record count to the top left of the DataTable
*/

////////////////////////////////////////////////////////////////////////////////
// Globals /////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////

let featureFileMap = {};                      // Maps feature type to CSV file
let currentTierFilter = "";                   // Default tier
let loadedData = [];                          // Parsed data from current CSV
let currentCsvPath = "";                      // Current CSV path
let currentTypeKey = "";                      // Name of column used for filtering types
let currentColKey = "";                       // Name of column to hide
let currentFeatureType = "";                  // Selected feature type
let order_array = false;                      // Whetther to order by presence column

let optional_columns = [];                    // Optional columns to display
let hide_cols = [];                           // Indeces of optional columns

let types = {};                    // Attribute type map (for sidebar)
let descriptions = {};             // Attribute descriptions (for sidebar)

////////////////////////////////////////////////////////////////////////////////
// Entry Point /////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////

window.addEventListener("DOMContentLoaded", () => {
  const page = document.body.getAttribute("data-page");
  let csv_fp;

  // Determine CSV index based on page
  switch (page) {
    case "presence_tables_page":
      csv_fp = "../data/presence_index.csv";
      optional_columns = ["optional","forbidden","conditionally_required","conditionally_forbidden"]
      break;
    case "attributes_tables_page":
      csv_fp = "../data/attributes_index.csv";
      break;
    case "types_page":
      csv_fp = "../data/types_index.csv";
      break;
    case "metadata_page":
      csv_fp = "../data/Metadata.csv";
      order_array = true // order by required/recommended
  }

  // determine which filepath to use
  let img_fp = "..";
  // page null is the homepage and has a different path to the image
  if (page === "homepage") {
    img_fp = "gatis_explorer";
  }

  // add banner image
  if (document.getElementById("banner-image")) {
    document.getElementById('banner-image').innerHTML = `
      <a href="${img_fp}/pages/attributions.html">
      <img src="${img_fp}/resources/GATIS Explorer Banner Graphic_new photos_72dpi.png" alt="Grid of six images showing people using active transportation infrastructure"></img>
      </a>
      `;
  }
  
  // add a return to main page button
    if (document.getElementById("return_to_main_page")) {
      document.getElementById('return_to_main_page').innerHTML = `
        <div style="padding-top:20px;">  
          <a href="../../index.html" class="link-button">Return to main page</a>
        </div>
        `;
    }
    
  // add the footer
  if (document.getElementById("std_footer")) {
    document.getElementById('std_footer').innerHTML = `
    <div><img src="${img_fp}/resources/GATIS_logo.png" alt="GATIS logo" style="height:120px; align-items: center"></div>  
    <p>
      Maintained by the
      <a href="https://github.com/dotbts/BPA" style="color:#d9e021">National Collaboration for Bicycle, Pedestrian, and Active Transportation Infrastructure Data (NC-BPAID)</a>
      </p>
      <p><a href="${img_fp}/pages/attributions.html" style="color:#d9e021">Image Attributions</a></p>
      `;
  }
  
  // If metadata, you just need to display the table and have the tier buttons
  if (page == "metadata_page") {
    // load tier buttons
    fetchAndRender(csv_fp);
    initTierButtons();
  }
  
  // page null is homepage
  if (page != null) {
    // Init dynamic elements based on page layout
    loadFeatureButtons(csv_fp);
    initTierButtons();
    initSidebarClickAway();
  }

});

////////////////////////////////////////////////////////////////////////////////
// Button Initializers /////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////

function initTierButtons() {
  // check if regular or cumulative version exists
  let tierContainer;
  if (document.getElementById("tierButtons")) {
    tierContainer = document.getElementById("tierButtons");
  } else if (document.getElementById("tierButtons_cumulative")) {
    tierContainer = document.getElementById("tierButtons_cumulative");
  } else {
    return;
  }

  tierContainer.querySelectorAll("button").forEach(btn => {
    btn.addEventListener("click", () => {
      currentTierFilter = btn.dataset.tier;

      // Highlight active button
      tierContainer.querySelectorAll("button").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      if (loadedData.length > 0 && currentTypeKey) {
        applyFiltersAndRender("tableContainer", "dynamicDataTable", currentTypeKey);
      } else if (currentCsvPath) {
        fetchAndRender(currentCsvPath, "tableContainer", "dynamicDataTable");
      }
    });
  });
}

function initSidebarClickAway() {
  if (!document.getElementById("sidebar")) {
    return;
  }
  
  document.addEventListener("click", (e) => {
    const sidebar = document.getElementById("sidebar");
    const clickedInside = sidebar.contains(e.target);
    const clickedDefinition = e.target.classList.contains("clickable");

    if (!clickedInside && !clickedDefinition) {
      sidebar.classList.remove("open");
    }
  });

  const closeBtn = document.getElementById("close-sidebar");
  if (closeBtn) {
    closeBtn.onclick = () => {
      document.getElementById("sidebar").classList.remove("open");
    };
  }
}

////////////////////////////////////////////////////////////////////////////////
// Feature Buttons + CSV Load //////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////

function loadFeatureButtons(csv_fp) {
  fetch(csv_fp)
    .then(res => res.text())
    .then(csvText => {
      const data = Papa.parse(csvText, { header: true, skipEmptyLines: true }).data;
      const container = document.getElementById("featureTypeButtons");

      featureFileMap = {};

      data.forEach(row => {
        const type = row.FeatureType;
        const file = row.FileName;

        if (type && file) {
          featureFileMap[type] = file;

          const btn = document.createElement("button");
          btn.textContent = type;
          btn.dataset.feature = type;
          btn.className = "feature-type-btn";

          btn.addEventListener("click", () => {
            document.querySelectorAll(".feature-type-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            const path = `../data/${file}`;
            currentCsvPath = path;
            currentFeatureType = type;

            fetchAndRender(path, "tableContainer", "dynamicDataTable");
            load_info();
          });

          container.appendChild(btn);
        }
      });
    });
}

////////////////////////////////////////////////////////////////////////////////
// CSV Parse + Render Logic ////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////

function fetchAndRender(csvUrl, containerId, tableId) {
  fetch(csvUrl)
    .then(res => res.text())
    .then(csvText => {
      loadedData = Papa.parse(csvText, { header: true, skipEmptyLines: true }).data;

      if (loadedData.length === 0) {
        document.getElementById(containerId).innerHTML = `<p>Error no data in ${csv_url}</p>`;
        return;
      }

      currentTypeKey = Object.keys(loadedData[0])[0];
      const uniqueTypes = [...new Set(loadedData.map(row => row[currentTypeKey]))].filter(Boolean);

      renderTypeCheckboxes(uniqueTypes, containerId, tableId, currentTypeKey);
      columnCheckboxes(optional_columns, containerId, tableId);
      applyFiltersAndRender(containerId, tableId, currentTypeKey);
    });
}

function renderTypeCheckboxes(uniqueTypes, containerId, tableId) {
  const container = document.getElementById("typeCheckboxes");
  if (!container) return; // if this element doesn't exist then skip

  container.innerHTML = ""; // clears the types out

  const allCheckbox = document.createElement("input");
  allCheckbox.type = "checkbox";
  allCheckbox.id = "typeAll";
  allCheckbox.checked = true;

  const allLabel = document.createElement("label");
  allLabel.htmlFor = "typeAll";
  allLabel.textContent = " Toggle all";

  const allRow = document.createElement("div");
  allRow.appendChild(allCheckbox);
  allRow.appendChild(allLabel);
  container.appendChild(allRow);

  const row = document.createElement("div");
  row.style.display = "flex";
  row.style.flexWrap = "wrap";
  row.style.gap = "10px";

  uniqueTypes.forEach(type => {
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.className = "type-filter";
    cb.value = type;
    cb.checked = true;
    cb.id = `checkbox-${type}`;

    const label = document.createElement("label");
    label.htmlFor = cb.id;
    label.textContent = type;

    const wrapper = document.createElement("div");
    wrapper.appendChild(cb);
    wrapper.appendChild(label);
    row.appendChild(wrapper);
  });

  container.appendChild(row);

  allCheckbox.addEventListener("change", () => {
    const checkAll = allCheckbox.checked;
    document.querySelectorAll(".type-filter").forEach(cb => cb.checked = checkAll);
    applyFiltersAndRender(containerId, tableId, currentTypeKey);
  });

  document.querySelectorAll(".type-filter").forEach(cb => {
    cb.addEventListener("change", () => {
      const all = document.querySelectorAll(".type-filter");
      const checked = document.querySelectorAll(".type-filter:checked");
      allCheckbox.checked = all.length === checked.length;
      applyFiltersAndRender(containerId, tableId, currentTypeKey);
    });
  });
}

function columnCheckboxes(optional_columns, containerId, tableId) {
  const container = document.getElementById("optionalColumnsCheckboxes");
  if (!container) return; // if this div doesn't exist then skip

  container.innerHTML = ""; // clears existing content out

  // first is the show both check box
  const allCheckbox = document.createElement("input");
  allCheckbox.type = "checkbox";
  allCheckbox.id = "showAllCols";
  allCheckbox.checked = false; // don't have checked by default

  const allLabel = document.createElement("label");
  allLabel.htmlFor = "showAllCols";
  allLabel.textContent = "Toggle all";

  const allRow = document.createElement("div");
  allRow.appendChild(allCheckbox);
  allRow.appendChild(allLabel);
  container.appendChild(allRow);

  // then the other checkboxes
  const row = document.createElement("div");
  row.style.display = "flex";
  row.style.flexWrap = "wrap";
  row.style.gap = "10px";

  optional_columns.forEach(col => {
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.className = "col-filter";
    cb.value = col;
    cb.checked = false;
    cb.id = `checkbox-${col}`;

    const label = document.createElement("label");
    label.htmlFor = cb.id;
    label.textContent = col;

    const wrapper = document.createElement("div");
    wrapper.appendChild(cb);
    wrapper.appendChild(label);
    row.appendChild(wrapper);
  });

  container.appendChild(row);

  // callback functions

  // if the checkAll checked then apply it's status to all the other checkboxes
  allCheckbox.addEventListener("change", () => {
    const checkAll = allCheckbox.checked;
    document.querySelectorAll(".col-filter").forEach(cb => cb.checked = checkAll);
    applyFiltersAndRender(containerId, tableId, currentTypeKey);
  });

  // otherwise just monitor changes in the check boxes
  document.querySelectorAll(".col-filter").forEach(cb => {
    cb.addEventListener("change", () => {
      const all = document.querySelectorAll(".col-filter");
      const checked = document.querySelectorAll(".col-filter:checked");
      allCheckbox.checked = all.length === checked.length;
      applyFiltersAndRender(containerId, tableId, currentTypeKey);
    });
  });
}

function applyFiltersAndRender(containerId, tableId, typeKey) {
  let filtered = [...loadedData];
  
  // order by presnce column
  if (order_array) {
    filtered.sort((a, b) => {
      const presenceA = a.presence;
      const presenceB = b.presence;
      if (presenceA < presenceB) return 1;
      if (presenceA > presenceB) return -1;
      return 0;
  })};

  // add or remove optional columns
  // update hide cols
  hide_cols = [] // clear hide_cols
  // retreive from DOM
  document.querySelectorAll(".col-filter").forEach((cb) => {
    if (cb.checked === false) {
      hide_cols.push(cb.value)
    }
  });

  // loop through column names to get indeces
  let hide_cols_idx = [];
  if (hide_cols.length > 0) {
    for (let i = 0; i < Object.keys(filtered[0]).length; i++) {
      for (let z = 0; z < hide_cols.length; z++) {
        if (hide_cols[z] === Object.keys(filtered[0])[i]) {
          hide_cols_idx.push(i)
        }
      }
    }
  };

  // this shows all values
  if (document.getElementById("tierButtons") && currentTierFilter === "Show All") {
  // this triggers want to use cumulative
  } else if (document.getElementById("tierButtons_cumulative") && currentTierFilter != "") {
    // get Tier integer from string
    tier_int = parseInt(currentTierFilter.slice(-1));
    const feature_type_array_filter = [];
    for (let i = 0; i < tier_int + 1; i++) {
      feature_type_array_filter.push(`Tier ${i}`)
    }
    filtered = filtered.filter(row => feature_type_array_filter.includes(row.Tier));
  } else if (document.getElementById("tierButtons") && currentTierFilter) {
    filtered = filtered.filter(row => row.Tier === currentTierFilter);
  }

  // handles the type checkboxes? or the edge/node type boxes?
  const typeCheckboxesChecked = document.querySelectorAll(".type-filter:checked");
  if (typeCheckboxesChecked.length) {
    const checkedTypes = Array.from(typeCheckboxesChecked).map(cb => cb.value);
    filtered = filtered.filter(row => checkedTypes.includes(row[typeKey]));
  } else if (document.querySelectorAll(".type-filter").length) {
    filtered = [{}];
    Object.keys(loadedData[0]).forEach(key => (filtered[0][key] = ""));
  }

  document.getElementById(containerId).innerHTML = renderAutoTable(filtered, tableId);

  // creates the datatable
  $(`#${tableId}`).DataTable({
    destroy: true,
    paging: false,
    info: true,
    ordering: false,
    searching: true, // enables the filter boxes
    autoWidth: false, // set to false so column width is consistent across types/tiers
    columnDefs: [
      {
        targets: hide_cols_idx,
        visible: false
      }
    ],
    initComplete: function () {
      this.api().columns().every(function () {
        const column = this;
        $('input', this.header()).on('keyup change clear', function () {
          column.search(this.value).draw();
        });
      });
      setTimeout(() => {
        // use this to add hyperlinks to the attributes, just put in the column name
        renderTagsByColumnName(tableId,capitalizeFirstLetter("required"));
        renderTagsByColumnName(tableId,capitalizeFirstLetter("recommended"));
        renderTagsByColumnName(tableId,capitalizeFirstLetter("conditionally_required"));
        renderTagsByColumnName(tableId,capitalizeFirstLetter("optional"));
        renderTagsByColumnName(tableId,capitalizeFirstLetter("forbidden"));
      }, 0);
    },
  });
}

function renderAutoTable(rows, tableId) {
  // this function creates the HTML table
  
  // returns this message if now rows are present due to the tier buttons
  if (rows.length === 0) return "<p>No required or recommended features for this Tier</p>";

  const headers = Object.keys(rows[0]);
  const headerHtml = headers.map(h => `<th>${capitalizeFirstLetter(h)}</th>`).join("");
  const filterRowHtml = headers.map(() => `<th><input type="text" placeholder="Filter..." /></th>`).join("");
  
  // creates the rows and turns newline \n into <br> so it's rendered properly
  const rowsHtml = rows.map(row =>
    `<tr>${headers.map(h => `<td>${(row[h] || "").toString().replace(/\n/g, "<br>")}</td>`).join("")}</tr>`
  ).join("");
  
  return `
    <table id="${tableId}" class="display">
      <thead>
        <tr>${headerHtml}</tr>
        <tr>${filterRowHtml}</tr>
      </thead>
      <tbody>${rowsHtml}</tbody>
    </table>
  `;
}

////////////////////////////////////////////////////////////////////////////////
// Sidebar Logic ///////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////

function load_info() {
  types = {};
  descriptions = {};
  // bug fix: lowercase the current feature type so it find the right file name
  fetch(`../data/attribute_tables/${currentFeatureType.toLowerCase()}_attributes.csv`)
    .then(response => response.text())
    .then(csvText => {
      const data = Papa.parse(csvText, { header: true, skipEmptyLines: true }).data;
      data.forEach(row => {
        types[row.Name] = row.Type;
        descriptions[row.Name] = row.Description;
      });
    });
}

function renderTagsByColumnName(tableId, columnName) {
  /*
  this function highlights the attribute names and makes the sidebar appear
  when you click on one of the attribute names
  */
  
  const table = document.getElementById(tableId);
  const headers = table.querySelectorAll("thead th");

  let colIndex = -1;
  headers.forEach((th, i) => {
    if (th.textContent.trim().toLowerCase() === columnName.toLowerCase()) colIndex = i;
  });

  if (colIndex === -1) return;

  const rows = table.querySelectorAll("tbody tr");
  rows.forEach(row => {
    const cell = row.children[colIndex];
    if (!cell || cell.textContent === "--") return; // don't add links to blank cells

    const tags = cell.textContent.split(',').map(t => t.trim()).filter(Boolean);
    cell.innerHTML = '';

    tags.forEach((tag, i) => {
      const span = document.createElement("span");
      span.textContent = tag;
      span.className = "clickable";
      span.onclick = () => showDefinition(tag);
      cell.appendChild(span);
      // if (i < tags.length - 1) cell.appendChild(document.createTextNode("/"));
    });
  });
}

function showDefinition(term) {
  const def = (descriptions[term] || "No description").replace(/\n/g, "<br>");
  const type = types[term] || "No type";

  document.getElementById('definition-text').innerHTML = `
    <h2>${term}</h2>
    <h3>Definition</h3>
    ${def}
    <h3>Type</h3>
    ${type}
  `;

  document.getElementById('sidebar').classList.add('open');
}

////////////////////////////////////////////////////////////////////////////////
// Utility Functions ///////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////

function capitalizeFirstLetter(val) {
    // replace underscores with space
    val = String(val).replace("_"," ")

    // capitalize all first letters
    val = val.replace(/\b\w/g, char => char.toUpperCase());

    return val;
}