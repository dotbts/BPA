// hide these by default
  const AUTO_HIDE_TYPES = new Set([
    "esriFieldTypeBlob","esriFieldTypeGeometry","esriFieldTypeGlobalID",
    "esriFieldTypeGUID","esriFieldTypeInteger","esriFieldTypeOID"
  ]);
  const AUTO_HIDE_ATTRIBUTES = new Set(["Shape__Area","Shape__Length","Shape_Length"]);

  // column config: key, title, hidden, link, filter_type ('number'|'search'|'select'), collapse (bool), relative_col_width (number)
  const TABLES = [
    {
      id: 'table1',
      title: 'References',
      src: '../../resources/compendium/data/references.json',
      columns: [
        { key: 'dataset_id', title: 'Dataset ID', filter_type: 'select', relative_col_width: 3 },
        { key: 'dataset_name', title: 'Dataset Name', hidden: true, filter_type: 'search', relative_col_width: 1 },
        { key: 'description', title: 'Description', filter_type: 'search', collapse: true, relative_col_width: 3 },
        { key: 'entity', title: 'Entity', filter_type: 'select', relative_col_width: 2 },
        { key: 'city', title: 'City', filter_type: 'select', relative_col_width: 1 },
        { key: 'state', title: 'State', filter_type: 'select', relative_col_width: 1 },
        { key: 'county', title: 'County', hidden: true, filter_type: 'select', relative_col_width: 1 },
        // { key: 'geographic_area', title: 'Geographic Area', filter_type: 'select', relative_col_width: 1 },
        { key: 'info_url', title: 'Info URL', filter_type: 'search', link: true, relative_col_width: 1 },
        { key: 'row_count', title: 'Row Count', filter_type: 'number', relative_col_width: 1 },
        { key: 'column_count', title: 'Column Count', filter_type: 'number', relative_col_width: 1 },
        { key: 'tags', title: 'Tags', filter_type: 'select', relative_col_width: 1 },
        { key: 'api_endpoint', title: 'API Endpoint', hidden: true, link: true, filter_type: 'search', relative_col_width: 1 },
        { key: 'api_id', title: 'API ID', hidden: true, filter_type: 'select', relative_col_width: 1 }
      ],
      pageLength: 10,
      publishesVisibleKeys: true,
    },
    {
      id: 'table2',
      title: 'Attributes',
      src: '../../resources/compendium/data/attributes.json',
      columns: [
        { key: 'attribute_id', title: 'Attribute ID', hidden: true, filter_type: 'search', relative_col_width: 1 },
        { key: 'dataset_id', title: 'Dataset ID', relative_col_width: 1 },
        { key: 'attribute_alias', title: 'Attribute', filter_type: 'search', relative_col_width: 2 },
        { key: 'data_type', title: 'Data Type', filter_type: 'select', relative_col_width: 1 },
        { key: 'unique_values', title: 'Unique Values', filter_type: 'search', collapse: true, relative_col_width: 3 },
        { key: 'unique_count', title: 'Unique Count', filter_type: 'number', relative_col_width: 1 },
        { key: 'null_percent', title: 'Null Percent', filter_type: 'number', relative_col_width: 1 },
        { key: 'min', title: 'Minimum', hidden: true, filter_type: 'number', relative_col_width: 1 },
        { key: 'max', title: 'Maximum', hidden: true, filter_type: 'number', relative_col_width: 1 },
        { key: 'avg', title: 'Average', hidden: true, filter_type: 'number', relative_col_width: 1 },
        { key: 'sum', title: 'Sum', hidden: true, filter_type: 'number', relative_col_width: 1 }
      ],
      pageLength: 20,
      linkFrom: 'table1'  // this table receives visible dataset_id from table1
    }
  ];

  // Registry & utilities
  const TABLE_REGISTRY = new Map();
  
  function isNumeric(n){ return !isNaN(parseFloat(n)) && isFinite(n); }
  function getValue(obj, key) {
    if (!obj || typeof key !== 'string') return undefined;
    if (key.indexOf('.') === -1) return obj[key];
    return key.split('.').reduce((o,k) => (o && k in o) ? o[k] : undefined, obj);
  }
  function fmtNumberDisplay(n) {
    if (n == null || n === '') return '';
    const num = Number(n);
    if (!isFinite(num)) return String(n);
    if (num === 0) return '0';
    if (Math.abs(num) >= 0.001) {
      const rounded = Math.round(num);
      return rounded.toLocaleString();
    } else {
      return num.toExponential(2);
    }
  }
  function debounce(fn, ms=250){ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a), ms); }; }

  // CSV download (unchanged)
  function downloadCSVRaw(filename, rows, columns) {
    const cols = columns;
    const header = cols.map(c => (c.title||c.key).replace(/"/g,'""')).join(',');
    const lines = [header];
    for (const r of rows) {
      const vals = cols.map(c => {
        if (c.key === '__stats__') {
          const mn = getValue(r,'min'), mx = getValue(r,'max'), av = getValue(r,'avg'), su = getValue(r,'sum');
          const combined = { min: mn == null ? null : mn, max: mx == null ? null : mx, avg: av == null ? null : av, sum: su == null ? null : su };
          return `"${JSON.stringify(combined).replace(/"/g,'""')}"`;
        }
        const v = getValue(r, c.key);
        if (v == null) return '""';
        if (Array.isArray(v)) return `"${JSON.stringify(v).replace(/"/g,'""')}"`;
        return `"${String(v).replace(/"/g,'""')}"`;
      });
      lines.push(vals.join(','));
    }
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = filename; document.body.appendChild(link); link.click(); link.remove();
  }

  // Numeric expression parsing (unchanged)
  function tokenizeNumericExpr(s) {
    const tokens = []; let i=0; const reSpace=/\s/;
    while (i<s.length) {
      if (reSpace.test(s[i])) { i++; continue; }
      if (s[i] === '(' || s[i] === ')') { tokens.push({type:'paren', val:s[i]}); i++; continue; }
      if ((s[i]==='>'||s[i]==='<'||s[i]==='!'||s[i]==='=') && i+1<s.length) {
        const two = s.substr(i,2);
        if (two === '>=' || two === '<=' || two === '!=' || two === '==') {
          tokens.push({type:'op', val: two});
          i += 2;
          continue;
        }
      }
      if (s[i]==='>'||s[i]==='<'||s[i]==='=') { tokens.push({type:'op', val:s[i]}); i++; continue; }
      const remain = s.substr(i);
      const mAnd = remain.match(/^(AND)\b/i); if (mAnd) { tokens.push({type:'and'}); i+=mAnd[0].length; continue; }
      const mOr = remain.match(/^(OR)\b/i); if (mOr) { tokens.push({type:'or'}); i+=mOr[0].length; continue; }
      const mNum = remain.match(/^([+-]?\d+(\.\d+)?)/); if (mNum) { tokens.push({type:'num', val:mNum[1]}); i+=mNum[1].length; continue; }
      return { error: `Unexpected token at position ${i}: "${s[i]}"` };
    }
    return { tokens };
  }
  function parseNumericTokens(tokens) {
    let pos=0;
    const peek=()=>tokens[pos];
    const consume=(t)=>{ const tk=tokens[pos]; if(!tk) return null; if(t && tk.type!==t) return null; pos++; return tk; };
    function parseExpr(){ return parseOr(); }
    function parseOr() {
      let left = parseAnd(); if (!left) return null;
      while (peek() && peek().type === 'or') { consume('or'); const right = parseAnd(); if (!right) return null; const prev=left; left = v => prev(v) || right(v); }
      return left;
    }
    function parseAnd() {
      let left = parseAtom(); if (!left) return null;
      while (peek() && peek().type === 'and') { consume('and'); const right = parseAtom(); if (!right) return null; const prev=left; left = v => prev(v) && right(v); }
      return left;
    }
    function parseAtom() {
      const t = peek(); if (!t) return null;
      if (t.type==='paren' && t.val==='(') { consume('paren'); const expr=parseExpr(); if(!expr) return null; const next=consume(); if(!next||next.type!=='paren'||next.val!==')') return null; return expr; }
      const opTok = consume('op'); if (!opTok) return null;
      const numTok = consume('num'); if (!numTok) return null;
      const num = parseFloat(numTok.val);
      switch (opTok.val) {
        case '>': return v => { const nv = parseFloat(v); return isFinite(nv) && nv > num; };
        case '>=': return v => { const nv = parseFloat(v); return isFinite(nv) && nv >= num; };
        case '<': return v => { const nv = parseFloat(v); return isFinite(nv) && nv < num; };
        case '<=': return v => { const nv = parseFloat(v); return isFinite(nv) && nv <= num; };
        case '!=': case '==': return v => { const nv = parseFloat(v); return isFinite(nv) && nv !== num; };
        case '=': return v => { const nv = parseFloat(v); return isFinite(nv) && nv === num; };
        default: return null;
      }
    }
    const pred = parseExpr(); if (!pred) return { error:'Failed to parse expression' }; if (pos < tokens.length) return { error:'Unexpected trailing tokens' }; return { predicate: pred };
  }
  function buildNumericPredicateFromStringWithParens(input) {
    if (!input || !input.trim()) return { error: 'Empty' };
    const normalized = input.replace(/≠/g,'!=');
    const tk = tokenizeNumericExpr(normalized); if (tk.error) return { error: tk.error };
    const parsed = parseNumericTokens(tk.tokens); if (parsed.error) return { error: parsed.error };
    const predicate = parsed.predicate; predicate._exprString = input; return { predicate };
  }

  // Description preview builder (now controlled by column.collapse)
  function makeDescriptionCell(text) {
    const wrapper = document.createElement('div');
    const preview = document.createElement('div');
    preview.className = 'desc-preview'; // relies on your CSS that sets max-height, overflow, line-height
    preview.tabIndex = 0;
    preview.setAttribute('role','button');
    preview.setAttribute('aria-expanded','false');

    const safeText = text == null ? '' : (Array.isArray(text) ? text.map(x => x==null ? '' : String(x)).join(', ') : String(text));
    preview.textContent = safeText;
    if (safeText) preview.title = safeText;

    wrapper.appendChild(preview);

    // Add hint element but hide by default
    const hint = document.createElement('span');
    hint.className = 'desc-hint';
    hint.style.display = 'none';
    hint.textContent = '(click text above to show more)';
    wrapper.appendChild(hint);

    // helper that checks if preview content is clipped
    function checkClipped() {
      // clientHeight includes padding; scrollHeight is content height
      const clipped = preview.scrollHeight > preview.clientHeight + 1; // +1 tolerance for fractional pixels
      if (clipped) {
        hint.style.display = '';
        preview.setAttribute('aria-hidden', 'false');
        preview.setAttribute('role','button');
        preview.tabIndex = 0;
      } else {
        hint.style.display = 'none';
        preview.removeAttribute('role');
        preview.tabIndex = -1;
      }
    }

    // toggle expansion
    function setExpanded(expanded) {
      if (expanded) {
        preview.classList.add('expanded'); // your CSS uses .expanded to remove max-height
        preview.setAttribute('aria-expanded','true');
        hint.textContent = '(click text above to show less)';
      } else {
        preview.classList.remove('expanded');
        preview.setAttribute('aria-expanded','false');
        hint.textContent = '(click text above to show more)';
        // scrollIntoView to keep context
        if (preview.scrollIntoView) preview.scrollIntoView({ block:'nearest' });
      }
    }

    // user interactions
    preview.addEventListener('click', () => {
      const isExp = preview.classList.contains('expanded');
      setExpanded(!isExp);
    }, { passive: true });

    preview.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        const isExp = preview.classList.contains('expanded');
        setExpanded(!isExp);
      }
    });

    // wait until element is attached and styles applied
    requestAnimationFrame(() => {
      checkClipped();
    });

    // Optional: if column/table can resize (e.g., user resizes window), re-check. Use ResizeObserver if available.
    let ro;
    if (window.ResizeObserver) {
      ro = new ResizeObserver(() => {
        // if expanded, we don't need a hint; if collapsed, re-evaluate clipping
        if (!preview.classList.contains('expanded')) checkClipped();
      });
      ro.observe(preview);
      // observe wrapper parent width too if layout changes when table column resizes
      ro.observe(wrapper.parentElement || document.body);
    } else {
      // fallback: check on window resize
      window.addEventListener('resize', checkClipped);
    }

    // Clean-up: If you ever remove this cell, disconnect resize observer
    // wrapper.cleanup = () => { if (ro) ro.disconnect(); window.removeEventListener('resize', checkClipped); };

    return wrapper;
}

  // Build table: major refactor to use filter_type, collapse, relative_col_width
  async function buildTable(cfg, container) {
    let data;
    try {
      const res = await fetch(cfg.src);
      if (!res.ok) throw new Error(`Failed to fetch ${cfg.src}: ${res.status}`);
      data = await res.json();
      if (!Array.isArray(data)) throw new Error('JSON must be an array of objects');
    } catch (err) {
      container.innerHTML = `<div class="table-wrap"><h2>${cfg.title}</h2><div class="no-data">Error: ${err.message}</div></div>`;
      return;
    }

    // Resolve columns: copy config; if no columns provided, infer (minimal inference)
    let cols = cfg.columns && cfg.columns.length ? cfg.columns.map(c => ({...c})) : (data.length === 0 ? [] : Object.keys(data[0]).map(k => ({ key:k, title:k, filter_type: isNumeric(data[0][k]) ? 'number' : (Array.isArray(data[0][k]) ? 'select' : 'search'), relative_col_width: 1 })));
    const visibleMap = new Map(cols.map(c => [c.key, !c.hidden]));
    const showCombinedStats = cfg.id === 'table2';
    if (showCombinedStats && !visibleMap.has('__stats__')) visibleMap.set('__stats__', true);

    function isColumnVisible(key){ return visibleMap.get(key) !== false; }
    function setColumnVisible(key, yes){ visibleMap.set(key, !!yes); renderTable(); }
    function visibleColsArr(){
      const base = cols.filter(c => isColumnVisible(c.key));
      if (showCombinedStats) {
        const filtered = base.filter(c => !['min','max','avg','sum'].includes(c.key));
        if (isColumnVisible('__stats__')) filtered.push({ key: '__stats__', title: 'Statistics', filter_type: 'select', relative_col_width: 1 });
        return filtered;
      }
      return base;
    }

    // state
    const state = {
      data,
      columnFilters: new Map(),
      externalKeyFilter: null,
      externalKeyFilterFromLinkedTable: null,
      sortKey: 'dataset_id',
      sortDir: 1,
      page: 1,
      pageLength: cfg.pageLength || 10,
      showAutoHiddenAttrs: false,
      _effectiveExternalKeyFilter: null
    };

    // Helpers

    function uniqueValuesForColumn(key, rows) {
      const set = new Map();
      for (const row of rows) {
        const raw = getValue(row, key);
        if (Array.isArray(raw)) {
          for (const it of raw) {
            const s = it == null ? '' : String(it);
            set.set(s, (set.get(s)||0)+1);
          }
        } else if (raw != null && typeof raw === 'string' && raw.includes(',')) {
          raw.split(',').map(x=>x.trim()).forEach(x=>set.set(x,(set.get(x)||0)+1));
        } else {
          const s = raw == null ? '' : String(raw);
          set.set(s, (set.get(s)||0)+1);
        }
      }
      const arr = Array.from(set.entries());
      arr.sort((a,b)=>{
        if (isNumeric(a[0]) && isNumeric(b[0])) return Number(a[0]) - Number(b[0]);
        return String(a[0]).localeCompare(String(b[0]));
      });
      return arr;
    }

    function composeExternalKeyFilter() {
      const localSet = state.externalKeyFilter;
      const linked = state.externalKeyFilterFromLinkedTable;
      if (localSet && linked) {
        const intersect = new Set();
        localSet.forEach(k => { if (linked.has(k)) intersect.add(k); });
        return intersect;
      } else if (localSet) return localSet;
      else if (linked) return linked;
      return null;
    }

    // apply filters & sort
    function applyFiltersAndSort_internal() {
      let rows = state.data.slice();
      for (const [colKey, filterVal] of state.columnFilters.entries()) {
        if (!filterVal) continue;
        rows = rows.filter(row => {
          if (colKey === '__stats__' && typeof filterVal === 'function') {
            try { return filterVal(row); } catch (e) { return false; }
          }
          const raw = getValue(row, colKey);
          if (typeof filterVal === 'function') {
            try { return filterVal(raw); } catch (e) { return false; }
          }
          if (Array.isArray(raw)) {
            if (filterVal instanceof Set) return raw.some(x => filterVal.has(String(x ?? '')));
            return false;
          }
          if (filterVal instanceof Set) return filterVal.has(String(raw ?? ''));
          return true;
        });
      }

      state._effectiveExternalKeyFilter = composeExternalKeyFilter();
      if (state._effectiveExternalKeyFilter) {
        rows = rows.filter(row => state._effectiveExternalKeyFilter.has(String(getValue(row,'dataset_id'))));
      }

      if (state.sortKey) {
        const col = cols.find(c => c.key === state.sortKey) || {};
        const type = col.filter_type === 'number' ? 'number' : (col.filter_type === 'select' ? 'array' : 'string');
        rows.sort((a,b)=>{
          let av = getValue(a, state.sortKey), bv = getValue(b, state.sortKey);
          if (type === 'array') { av = Array.isArray(av) ? (av[0] ?? '') : av; bv = Array.isArray(bv) ? (bv[0] ?? '') : bv; }
          if (col.filter_type === 'number') { av = parseFloat(av); bv = parseFloat(bv); av = isNaN(av)?-Infinity:av; bv = isNaN(bv)?-Infinity:bv; }
          else { av = av == null ? '' : String(av).toLowerCase(); bv = bv == null ? '' : String(bv).toLowerCase(); }
          if (av < bv) return -1 * state.sortDir;
          if (av > bv) return 1 * state.sortDir;
          return 0;
        });
      }

      // auto hide behavior for attributes table
      if (cfg.id === 'table2' && !state.showAutoHiddenAttrs) {
        rows = rows.filter(r => !AUTO_HIDE_TYPES.has(String(getValue(r,'data_type'))));
        rows = rows.filter(r => !AUTO_HIDE_ATTRIBUTES.has(String(getValue(r,'attribute_id'))));
        rows = rows.filter(r => {
          const np = getValue(r, 'null_percent');
          return !(np != null && Number(np) === 100);
        });
      }
      return rows;
    }

    // external key filter receiver
    function receiveExternalKeyFilter(keysSet, fromTableId) {
      state.externalKeyFilterFromLinkedTable = keysSet ? new Set(Array.from(keysSet).map(String)) : null;
      state._effectiveExternalKeyFilter = composeExternalKeyFilter();
      state.page = 1;
      renderTable();
    }

    // build DOM
    const wrap = document.createElement('div'); wrap.className = 'table-wrap';
    wrap.innerHTML = `
      <h2>${cfg.title}</h2>
      <div class="controls">
        <div class="left">
          ${cfg.id === 'table1' ? '<button class="cols-btn">Show/hide columns ▾</button>' : '<button class="cols-btn" style="display:none;">Show/hide columns ▾</button>'}
          <button class="csv-btn">Download CSV</button>
          ${cfg.id === 'table2' ? '<button class="toggle-autohide small">Show hidden metadata rows</button>' : ''}
        </div>
        <div class="pager small" aria-hidden="true"></div>
      </div>
      <div class="table-area"></div>
    `;
    container.appendChild(wrap);
    const pagerDiv = wrap.querySelector('.pager');
    const tableArea = wrap.querySelector('.table-area');
    const colsBtn = wrap.querySelector('.cols-btn');
    const csvBtn = wrap.querySelector('.csv-btn');
    const toggleAutoBtn = wrap.querySelector('.toggle-autohide');

    // columns menu
    let colsMenu;
    colsBtn.addEventListener('click', () => {
      if (colsMenu) { colsMenu.remove(); colsMenu = null; return; }
      colsMenu = document.createElement('div'); colsMenu.className = 'cols-menu';
      cols.forEach(c => {
        if (showCombinedStats && ['min','max','avg','sum'].includes(c.key)) return;
        const id = `colchk-${cfg.id}-${c.key}`;
        const label = document.createElement('label');
        const chk = document.createElement('input'); chk.type='checkbox'; chk.id=id; chk.checked = isColumnVisible(c.key);
        chk.addEventListener('change', () => { setColumnVisible(c.key, chk.checked); });
        label.appendChild(chk); label.appendChild(document.createTextNode(c.title || c.key));
        colsMenu.appendChild(label);
      });
      if (showCombinedStats) {
        const id = `colchk-${cfg.id}--stats`;
        const label = document.createElement('label');
        const chk = document.createElement('input'); chk.type='checkbox'; chk.id=id; chk.checked = isColumnVisible('__stats__');
        chk.addEventListener('change', () => { setColumnVisible('__stats__', chk.checked); });
        label.appendChild(chk); label.appendChild(document.createTextNode('Statistics'));
        colsMenu.appendChild(document.createElement('hr'));
        colsMenu.appendChild(label);
      }
      const rect = colsBtn.getBoundingClientRect();
      colsMenu.style.left = rect.left + 'px';
      colsMenu.style.top = (rect.bottom + window.scrollY + 6) + 'px';
      document.body.appendChild(colsMenu);
      setTimeout(()=> document.addEventListener('click', onDocCloseCols, { once: true }), 0);
      function onDocCloseCols(e){ if (!colsMenu.contains(e.target) && e.target !== colsBtn) { colsMenu.remove(); colsMenu=null; } }
    });

    csvBtn.addEventListener('click', () => {
      const filtered = applyFiltersAndSort_internal();
      const vcols = visibleColsArr();
      downloadCSVRaw(`${cfg.id}.csv`, filtered, vcols);
    });

    if (toggleAutoBtn) {
      toggleAutoBtn.addEventListener('click', () => {
        state.showAutoHiddenAttrs = !state.showAutoHiddenAttrs;
        toggleAutoBtn.textContent = state.showAutoHiddenAttrs ? 'Hide hidden types' : 'Show hidden types';
        renderTable();
      });
    }

    // filter dropdown container
    const filterDropdown = document.createElement('div'); filterDropdown.className = 'col-filter hidden';
    document.body.appendChild(filterDropdown);
    let outsideHandler = null;

    function onCheckboxChangeForColumn(colKey, checkboxList) {
      const checked = Array.from(checkboxList.querySelectorAll('input[type="checkbox"]:checked')).map(i => i.value);
      if (checked.length === 0) {
        state.columnFilters.set(colKey, new Set());
      } else {
        const allValues = Array.from(checkboxList.querySelectorAll('input[type="checkbox"]')).map(i => i.value);
        const allSame = checked.length === allValues.length;
        if (allSame) state.columnFilters.delete(colKey);
        else state.columnFilters.set(colKey, new Set(checked.map(v => String(v))));
      }
      state.page = 1;
      if (colKey === 'dataset_id' && cfg.linkFrom) {
        const ks = state.columnFilters.has('dataset_id') ? new Set(Array.from(state.columnFilters.get('dataset_id')).map(String)) : null;
        const linkedEntry = TABLE_REGISTRY.get(cfg.linkFrom);
        if (linkedEntry && typeof linkedEntry.instance.receiveExternalKeyFilter === 'function') {
          linkedEntry.instance.receiveExternalKeyFilter(ks, cfg.id);
        }
      }
      renderTable();
    }

    // open filter dropdown: behavior driven by column.filter_type
    // function openFilterDropdownForColumn(col, thElement) {
    //   if (col.filterable === false) return;
    //   filterDropdown.innerHTML = '';
    //   const closeBtn = document.createElement('button'); closeBtn.className='filter-close'; closeBtn.innerHTML='×'; filterDropdown.appendChild(closeBtn);
    //   closeBtn.addEventListener('click', hideFilterDropdown);
    //   const heading = document.createElement('h4'); heading.textContent = `Filter: ${col.title||col.key}`; filterDropdown.appendChild(heading);
    //   const smallInfo = document.createElement('div'); smallInfo.className = 'small'; filterDropdown.appendChild(smallInfo);

    //   const rowsExcludingThis = state.data.slice().filter(r => {
    //     for (const [k, fv] of state.columnFilters.entries()) {
    //       if (k === col.key || k === '__stats__') continue;
    //       if (!fv) continue;
    //       const raw = getValue(r,k);
    //       if (Array.isArray(raw)) {
    //         if (fv instanceof Set) {
    //           if (!raw.some(x => fv.has(String(x ?? '')))) return false;
    //         } else return false;
    //       } else if (typeof fv === 'function') {
    //         if (!fv(raw)) return false;
    //       } else if (fv instanceof Set) {
    //         if (!fv.has(String(raw ?? ''))) return false;
    //       }
    //     }
    //     const eff = composeExternalKeyFilter();
    //     if (eff && !eff.has(String(getValue(r,'dataset_id')))) return false;
    //     if (cfg.id === 'table2' && !state.showAutoHiddenAttrs) {
    //       if (AUTO_HIDE_TYPES.has(String(getValue(r,'data_type')))) return false;
    //       if (AUTO_HIDE_ATTRIBUTES.has(String(getValue(r,'attribute_id')))) return false;
    //       const np = getValue(r,'null_percent');
    //       if (np != null && Number(np) === 100) return false;
    //     }
    //     return true;
    //   });

    //   // statistics filter remains special
    //   if (col.key === '__stats__') {
    //     smallInfo.textContent = 'Filter by rows that have at least one non-null value among min/max/avg/sum.';
    //     const controls = document.createElement('div'); controls.style.marginTop='8px';
    //     const chk = document.createElement('input'); chk.type='checkbox'; chk.id = `stats-one-${cfg.id}`;
    //     const label = document.createElement('label'); label.style.display='flex'; label.style.alignItems='center'; label.style.gap='8px';
    //     label.appendChild(chk); label.appendChild(document.createTextNode('Has at least one stat (min/max/avg/sum)'));
    //     controls.appendChild(label); filterDropdown.appendChild(controls);
    //     const existing = state.columnFilters.get('__stats__');
    //     if (existing) chk.checked = true;
    //     chk.addEventListener('change', () => {
    //       if (chk.checked) {
    //         const pred = (row) => {
    //           const fields = ['min','max','avg','sum'];
    //           for (const f of fields) {
    //             const v = getValue(row,f);
    //             if (v != null && v !== '') return true;
    //           }
    //           return false;
    //         };
    //         state.columnFilters.set('__stats__', pred);
    //       } else {
    //         state.columnFilters.delete('__stats__');
    //       }
    //       state.page = 1; renderTable();
    //     });
    //     const rect = thElement.getBoundingClientRect();
    //     filterDropdown.style.left = Math.max(8, rect.left + window.scrollX) + 'px';
    //     filterDropdown.style.top = (rect.bottom + window.scrollY + 6) + 'px';
    //     filterDropdown.classList.remove('hidden');
    //     if (outsideHandler) document.removeEventListener('click', outsideHandler);
    //     outsideHandler = (e) => { if (!filterDropdown.contains(e.target) && !thElement.contains(e.target)) hideFilterDropdown(); };
    //     setTimeout(()=> document.addEventListener('click', outsideHandler), 0);
    //     return;
    //   }

    //   // If filter_type === 'search' -> text/regex input
    //   if (col.filter_type === 'search') {
    //     smallInfo.textContent = 'Text search (regex supported). Examples: "bike", "^(bike|pedestrian)$"';
    //     const input = document.createElement('input'); input.type='text'; input.className='col-search';
    //     input.placeholder = 'Enter text or regex';
    //     const current = state.columnFilters.get(col.key);
    //     input.value = (typeof current === 'function' && current._regexSource) ? current._regexSource : '';
    //     filterDropdown.appendChild(input);
    //     const err = document.createElement('div'); err.className='small'; err.style.color='crimson'; err.style.marginTop='6px'; filterDropdown.appendChild(err);
    //     const applyRegexDebounced = debounce(() => {
    //       const v = input.value.trim();
    //       if (!v) { state.columnFilters.delete(col.key); err.textContent = ''; state.page = 1; renderTable(); return; }
    //       try {
    //         const re = new RegExp(v, 'i');
    //         const pred = (raw) => {
    //           if (raw == null) return false;
    //           if (typeof raw === 'string') return re.test(raw);
    //           if (Array.isArray(raw)) return raw.some(x => re.test(String(x)));
    //           return false;
    //         };
    //         pred._regexSource = v;
    //         state.columnFilters.set(col.key, pred);
    //         err.textContent = '';
    //         state.page = 1; renderTable();
    //       } catch (e) {
    //         err.textContent = 'Invalid regex';
    //       }
    //     }, 300);
    //     input.addEventListener('input', applyRegexDebounced);
    //     const rect = thElement.getBoundingClientRect();
    //     filterDropdown.style.left = Math.max(8, rect.left + window.scrollX) + 'px';
    //     filterDropdown.style.top = (rect.bottom + window.scrollY + 6) + 'px';
    //     filterDropdown.classList.remove('hidden');
    //     if (outsideHandler) document.removeEventListener('click', outsideHandler);
    //     outsideHandler = (e) => { if (!filterDropdown.contains(e.target) && !thElement.contains(e.target)) hideFilterDropdown(); };
    //     setTimeout(()=> document.addEventListener('click', outsideHandler), 0);
    //     return;
    //   }

    //   // If filter_type === 'select' -> checkbox list with search + toggle
    //   if (col.filter_type === 'select') {
    //     smallInfo.textContent = `Toggle checkboxes to filter in/out rows.`;
    //     const searchVals = document.createElement('input'); searchVals.className='col-search'; searchVals.placeholder='Search values...';
    //     filterDropdown.appendChild(searchVals);
    //     const valCounts = uniqueValuesForColumn(col.key, rowsExcludingThis);
    //     const valsWrap = document.createElement('div'); valsWrap.className='vals'; filterDropdown.appendChild(valsWrap);
    //     function renderVals(filterText='') {
    //       valsWrap.innerHTML = '';
    //       const filteredVals = filterText ? valCounts.filter(v => v[0].toLowerCase().includes(filterText.toLowerCase())) : valCounts;
    //       filteredVals.forEach(([val,count]) => {
    //         const id = `chk-${cfg.id}-${col.key}-${btoa(String(val)).replace(/=/g,'')}`;
    //         const label = document.createElement('label');
    //         const inp = document.createElement('input'); inp.type='checkbox'; inp.id=id; inp.value = val;
    //         const currentSet = state.columnFilters.get(col.key) || null;
    //         const allCheckedByDefault = !currentSet;
    //         inp.checked = allCheckedByDefault ? true : currentSet.has(String(val));
    //         inp.addEventListener('change', () => onCheckboxChangeForColumn(col.key, valsWrap));
    //         label.appendChild(inp);
    //         label.appendChild(document.createTextNode(' ' + (val === '' ? '(empty)' : val)));
    //         const cntSpan = document.createElement('span'); cntSpan.className='val-count'; cntSpan.textContent = `(${count})`;
    //         label.appendChild(cntSpan);
    //         valsWrap.appendChild(label);
    //       });
    //     }
    //     renderVals();
    //     searchVals.addEventListener('input', () => renderVals(searchVals.value.trim()));
    //     const actions = document.createElement('div'); actions.className='actions';
    //     const toggleBtn = document.createElement('button'); toggleBtn.textContent='Toggle all';
    //     toggleBtn.addEventListener('click', () => {
    //       const allBoxes = Array.from(valsWrap.querySelectorAll('input[type="checkbox"]'));
    //       const allChecked = allBoxes.every(b => b.checked);
    //       allBoxes.forEach(b => b.checked = !allChecked);
    //       onCheckboxChangeForColumn(col.key, valsWrap);
    //     });
    //     actions.appendChild(toggleBtn);
    //     filterDropdown.appendChild(actions);
    //     const rect = thElement.getBoundingClientRect();
    //     filterDropdown.style.left = Math.max(8, rect.left + window.scrollX) + 'px';
    //     filterDropdown.style.top = (rect.bottom + window.scrollY + 6) + 'px';
    //     filterDropdown.classList.remove('hidden');
    //     if (outsideHandler) document.removeEventListener('click', outsideHandler);
    //     outsideHandler = (e) => { if (!filterDropdown.contains(e.target) && !thElement.contains(e.target)) hideFilterDropdown(); };
    //     setTimeout(()=> document.addEventListener('click', outsideHandler), 0);
    //     return;
    //   }

    //   // If filter_type === 'number' -> numeric expression
    //   if (col.filter_type === 'number') {
    //     smallInfo.textContent = 'Type one or more conditional expressions to filter numbers. Examples: (>=10 AND <=20) OR (=5)';
    //     const input = document.createElement('input'); input.type='text'; input.className='num-input'; input.placeholder='(>=10 AND <=20) OR (=5)';
    //     const current = state.columnFilters.get(col.key); input.value = current && current._exprString ? current._exprString : '';
    //     filterDropdown.appendChild(input);
    //     const hint = document.createElement('div'); hint.className='hint'; hint.textContent = 'Comparisons require an operator: =, !=, <, <=, >, >=.\nCombine with AND / OR and group with parentheses.';
    //     filterDropdown.appendChild(hint);
    //     const err = document.createElement('div'); err.className='small'; err.style.color='crimson'; err.style.marginTop='6px'; filterDropdown.appendChild(err);
    //     const debouncedApply = debounce(() => {
    //       const txt = input.value.trim();
    //       if (!txt) { state.columnFilters.delete(col.key); err.textContent=''; state.page=1; renderTable(); return; }
    //       const res = buildNumericPredicateFromStringWithParens(txt);
    //       if (res && res.error) { err.textContent = 'Parse error: ' + res.error; return; }
    //       if (!res || !res.predicate) { err.textContent = 'Invalid expression. Operators required and use AND/OR only.'; return; }
    //       const pred = res.predicate; pred._exprString = txt; state.columnFilters.set(col.key, pred); err.textContent=''; state.page=1; renderTable();
    //     }, 250);
    //     input.addEventListener('input', () => debouncedApply());
    //     const rect = thElement.getBoundingClientRect();
    //     filterDropdown.style.left = Math.max(8, rect.left + window.scrollX) + 'px';
    //     filterDropdown.style.top = (rect.bottom + window.scrollY + 6) + 'px';
    //     filterDropdown.classList.remove('hidden');
    //     if (outsideHandler) document.removeEventListener('click', outsideHandler);
    //     outsideHandler = (e) => { if (!filterDropdown.contains(e.target) && !thElement.contains(e.target)) hideFilterDropdown(); };
    //     setTimeout(()=> document.addEventListener('click', outsideHandler), 0);
    //     return;
    //   }

    //   smallInfo.textContent = `Filtering not available for filter_type: ${col.filter_type || '(none)'}`;
    //   const rect = thElement.getBoundingClientRect();
    //   filterDropdown.style.left = Math.max(8, rect.left + window.scrollX) + 'px';
    //   filterDropdown.style.top = (rect.bottom + window.scrollY + 6) + 'px';
    //   filterDropdown.classList.remove('hidden');
    //   if (outsideHandler) document.removeEventListener('click', outsideHandler);
    //   outsideHandler = (e) => { if (!filterDropdown.contains(e.target) && !thElement.contains(e.target)) hideFilterDropdown(); };
    //   setTimeout(()=> document.addEventListener('click', outsideHandler), 0);
    // }

    // open filter dropdown: behavior driven by column.filter_type
    function openFilterDropdownForColumn(col, thElement) {
      if (col.filterable === false) return;
      filterDropdown.innerHTML = '';
      const closeBtn = document.createElement('button'); closeBtn.className='filter-close'; closeBtn.innerHTML='×'; filterDropdown.appendChild(closeBtn);
      closeBtn.addEventListener('click', hideFilterDropdown);
      const heading = document.createElement('h4'); heading.textContent = `Filter: ${col.title||col.key}`; filterDropdown.appendChild(heading);
      const smallInfo = document.createElement('div'); smallInfo.className = 'small'; filterDropdown.appendChild(smallInfo);
      const rowsExcludingThis = state.data.slice().filter(r => {
        for (const [k, fv] of state.columnFilters.entries()) {
          if (k === col.key || k === '__stats__') continue;
          if (!fv) continue;
          const raw = getValue(r,k);
          if (Array.isArray(raw)) {
            if (fv instanceof Set) {
              if (!raw.some(x => fv.has(String(x ?? '')))) return false;
            } else return false;
          } else if (typeof fv === 'function') {
            if (!fv(raw)) return false;
          } else if (fv instanceof Set) {
            if (!fv.has(String(raw ?? ''))) return false;
          }
        }
        const eff = composeExternalKeyFilter();
        if (eff && !eff.has(String(getValue(r,'dataset_id')))) return false;
        if (cfg.id === 'table2' && !state.showAutoHiddenAttrs) {
          if (AUTO_HIDE_TYPES.has(String(getValue(r,'data_type')))) return false;
          if (AUTO_HIDE_ATTRIBUTES.has(String(getValue(r,'attribute_id')))) return false;
          const np = getValue(r,'null_percent');
          if (np != null && Number(np) === 100) return false;
        }
        return true;
      });

      // Helper to position dropdown inside viewport
      function positionDropdown() {
        const rect = thElement.getBoundingClientRect();

        // temporarily show filterDropdown for measurement
        filterDropdown.style.visibility = 'hidden';
        filterDropdown.classList.remove('hidden');

        const dropdownRect = filterDropdown.getBoundingClientRect();

        filterDropdown.style.visibility = '';
        const dropdownWidth = dropdownRect.width || 300;  // fallback estimate
        const dropdownHeight = dropdownRect.height || 400; // fallback estimate

        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const scrollX = window.scrollX;
        const scrollY = window.scrollY;

        let left = rect.left + scrollX;
        let top = rect.bottom + scrollY + 6;

        // Horizontal adjustment
        if (left + dropdownWidth > scrollX + viewportWidth) {
          left = Math.max(scrollX + 8, scrollX + viewportWidth - dropdownWidth - 8);
        }

        // Vertical adjustment
        if (top + dropdownHeight > scrollY + viewportHeight) {
          // position above the header cell if there's space
          const aboveTop = rect.top + scrollY - dropdownHeight - 6;
          top = aboveTop > scrollY ? aboveTop : scrollY + 8;
        }

        filterDropdown.style.left = left + 'px';
        filterDropdown.style.top = top + 'px';
      }

      // statistics filter remains special
      if (col.key === '__stats__') {
        smallInfo.textContent = 'Filter by rows that have at least one non-null value among min/max/avg/sum.';
        const controls = document.createElement('div'); controls.style.marginTop='8px';
        const chk = document.createElement('input'); chk.type='checkbox'; chk.id = `stats-one-${cfg.id}`;
        const label = document.createElement('label'); label.style.display='flex'; label.style.alignItems='center'; label.style.gap='8px';
        label.appendChild(chk); label.appendChild(document.createTextNode('Has at least one stat (min/max/avg/sum)'));
        controls.appendChild(label); filterDropdown.appendChild(controls);
        const existing = state.columnFilters.get('__stats__');
        if (existing) chk.checked = true;
        chk.addEventListener('change', () => {
          if (chk.checked) {
            const pred = (row) => {
              const fields = ['min','max','avg','sum'];
              for (const f of fields) {
                const v = getValue(row,f);
                if (v != null && v !== '') return true;
              }
              return false;
            };
            state.columnFilters.set('__stats__', pred);
          } else {
            state.columnFilters.delete('__stats__');
          }
          state.page = 1; renderTable();
        });
        positionDropdown();
        if (outsideHandler) document.removeEventListener('click', outsideHandler);
        outsideHandler = (e) => { if (!filterDropdown.contains(e.target) && !thElement.contains(e.target)) hideFilterDropdown(); };
        setTimeout(()=> document.addEventListener('click', outsideHandler), 0);
        return;
      }
      // If filter_type === 'search' -> text/regex input
      if (col.filter_type === 'search') {
        smallInfo.textContent = 'Text search (regex supported). Examples: "bike", "^(bike|pedestrian)$"';
        const input = document.createElement('input'); input.type='text'; input.className='col-search';
        input.placeholder = 'Enter text or regex';
        const current = state.columnFilters.get(col.key);
        input.value = (typeof current === 'function' && current._regexSource) ? current._regexSource : '';
        filterDropdown.appendChild(input);
        const err = document.createElement('div'); err.className='small'; err.style.color='crimson'; err.style.marginTop='6px'; filterDropdown.appendChild(err);
        const applyRegexDebounced = debounce(() => {
          const v = input.value.trim();
          if (!v) { state.columnFilters.delete(col.key); err.textContent = ''; state.page = 1; renderTable(); return; }
          try {
            const re = new RegExp(v, 'i');
            const pred = (raw) => {
              if (raw == null) return false;
              if (typeof raw === 'string') return re.test(raw);
              if (Array.isArray(raw)) return raw.some(x => re.test(String(x)));
              return false;
            };
            pred._regexSource = v;
            state.columnFilters.set(col.key, pred);
            err.textContent = '';
            state.page = 1; renderTable();
          } catch (e) {
            err.textContent = 'Invalid regex';
          }
        }, 300);
        input.addEventListener('input', applyRegexDebounced);
        positionDropdown();
        if (outsideHandler) document.removeEventListener('click', outsideHandler);
        outsideHandler = (e) => { if (!filterDropdown.contains(e.target) && !thElement.contains(e.target)) hideFilterDropdown(); };
        setTimeout(()=> document.addEventListener('click', outsideHandler), 0);
        return;
      }

      // If filter_type === 'select' -> checkbox list with search + toggle
      if (col.filter_type === 'select') {
        smallInfo.textContent = `Toggle checkboxes to filter in/out rows.`;
        const searchVals = document.createElement('input'); searchVals.className='col-search'; searchVals.placeholder='Search values...';
        filterDropdown.appendChild(searchVals);

        const valCounts = uniqueValuesForColumn(col.key, rowsExcludingThis);

        // valsWrap holds the checkbox list only — renderVals will only modify this element's innerHTML.
        const valsWrap = document.createElement('div'); valsWrap.className='vals'; filterDropdown.appendChild(valsWrap);

        // Create actions (and toggle button) *before* calling renderVals so the button is always present,
        // and so subsequent calls to renderVals() won't remove it.
        const actions = document.createElement('div'); actions.className='actions';
        const toggleBtn = document.createElement('button'); toggleBtn.type = 'button'; toggleBtn.textContent='Toggle all';
        toggleBtn.addEventListener('click', () => {
          // toggle only the checkboxes that are currently rendered inside valsWrap
          const allBoxes = Array.from(valsWrap.querySelectorAll('input[type="checkbox"]'));
          const allChecked = allBoxes.length > 0 && allBoxes.every(b => b.checked);
          allBoxes.forEach(b => b.checked = !allChecked);
          onCheckboxChangeForColumn(col.key, valsWrap);
        });
        actions.appendChild(toggleBtn);
        filterDropdown.appendChild(actions);

        function renderVals(filterText='') {
          // Only touch valsWrap — do not change actions or other nodes.
          valsWrap.innerHTML = '';
          const filteredVals = filterText ? valCounts.filter(v => v[0].toLowerCase().includes(filterText.toLowerCase())) : valCounts;
          filteredVals.forEach(([val,count]) => {
            const id = `chk-${cfg.id}-${col.key}-${btoa(String(val)).replace(/=/g,'')}`;
            const label = document.createElement('label');
            const inp = document.createElement('input'); inp.type='checkbox'; inp.id=id; inp.value = val;
            const currentSet = state.columnFilters.get(col.key) || null;
            const allCheckedByDefault = !currentSet;
            inp.checked = allCheckedByDefault ? true : currentSet.has(String(val));
            inp.addEventListener('change', () => onCheckboxChangeForColumn(col.key, valsWrap));
            label.appendChild(inp);
            label.appendChild(document.createTextNode(' ' + (val === '' ? '(empty)' : val)));
            const cntSpan = document.createElement('span'); cntSpan.className='val-count'; cntSpan.textContent = `(${count})`;
            label.appendChild(cntSpan);
            valsWrap.appendChild(label);
          });
          // If there are no values, show an informative message (keeps UI consistent)
          if (filteredVals.length === 0) {
            const msg = document.createElement('div');
            msg.className = 'small no-values';
            msg.textContent = '(no values)';
            valsWrap.appendChild(msg);
          }
        }

        renderVals();
        searchVals.addEventListener('input', () => renderVals(searchVals.value.trim()));

        positionDropdown();
        if (outsideHandler) document.removeEventListener('click', outsideHandler);
        outsideHandler = (e) => { if (!filterDropdown.contains(e.target) && !thElement.contains(e.target)) hideFilterDropdown(); };
        setTimeout(()=> document.addEventListener('click', outsideHandler), 0);
        return;
      }

      // If filter_type === 'number' -> numeric expression
      if (col.filter_type === 'number') {
        smallInfo.textContent = 'Type one or more conditional expressions to filter numbers. Examples: (>=10 AND <=20) OR (=5)';
        const input = document.createElement('input'); input.type='text'; input.className='num-input'; input.placeholder='(>=10 AND <=20) OR (=5)';
        const current = state.columnFilters.get(col.key); input.value = current && current._exprString ? current._exprString : '';
        filterDropdown.appendChild(input);
        const hint = document.createElement('div'); hint.className='hint'; hint.textContent = 'Comparisons require an operator: =, !=, <, <=, >, >=.\nCombine with AND / OR and group with parentheses.';
        filterDropdown.appendChild(hint);
        const err = document.createElement('div'); err.className='small'; err.style.color='crimson'; err.style.marginTop='6px'; filterDropdown.appendChild(err);
        const debouncedApply = debounce(() => {
          const txt = input.value.trim();
          if (!txt) { state.columnFilters.delete(col.key); err.textContent=''; state.page=1; renderTable(); return; }
          const res = buildNumericPredicateFromStringWithParens(txt);
          if (res && res.error) { err.textContent = 'Parse error: ' + res.error; return; }
          if (!res || !res.predicate) { err.textContent = 'Invalid expression. Operators required and use AND/OR only.'; return; }
          const pred = res.predicate; pred._exprString = txt; state.columnFilters.set(col.key, pred); err.textContent=''; state.page=1; renderTable();
        }, 250);
        input.addEventListener('input', () => debouncedApply());
        positionDropdown();
        if (outsideHandler) document.removeEventListener('click', outsideHandler);
        outsideHandler = (e) => { if (!filterDropdown.contains(e.target) && !thElement.contains(e.target)) hideFilterDropdown(); };
        setTimeout(()=> document.addEventListener('click', outsideHandler), 0);
        return;
      }
      smallInfo.textContent = `Filtering not available for filter_type: ${col.filter_type || '(none)'}`;
      positionDropdown();
      if (outsideHandler) document.removeEventListener('click', outsideHandler);
      outsideHandler = (e) => { if (!filterDropdown.contains(e.target) && !thElement.contains(e.target)) hideFilterDropdown(); };
      setTimeout(() => document.addEventListener('click', outsideHandler), 0);
    }

    function hideFilterDropdown() {
      filterDropdown.classList.add('hidden'); filterDropdown.innerHTML = '';
      if (outsideHandler) { document.removeEventListener('click', outsideHandler); outsideHandler = null; }
    }

    // pager UI
    function renderPager(total, totalPages) {
      pagerDiv.innerHTML = '';
      const info = document.createElement('span'); info.className = 'small'; info.textContent = `${total} row${total===1?'':'s'}`; pagerDiv.appendChild(info);
      const btnPrev = document.createElement('button'); btnPrev.textContent='Prev'; btnPrev.disabled = state.page <= 1; btnPrev.addEventListener('click', ()=>{ state.page = Math.max(1, state.page-1); renderTable(); });
      const btnNext = document.createElement('button'); btnNext.textContent='Next'; btnNext.disabled = state.page >= totalPages; btnNext.addEventListener('click', ()=>{ state.page = Math.min(totalPages, state.page+1); renderTable(); });
      const pageInfo = document.createElement('span'); pageInfo.className='small'; pageInfo.textContent = `Page `;
      const pageInput = document.createElement('input'); pageInput.type = 'number'; pageInput.min = 1; pageInput.max = totalPages; pageInput.value = state.page; pageInput.title = 'Type a page number and press Enter or click outside';
      pageInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') { let v = Number(pageInput.value) || 1; v = Math.min(Math.max(1, v), totalPages); state.page = v; renderTable(); } });
      pageInput.addEventListener('blur', () => { let v = Number(pageInput.value) || 1; v = Math.min(Math.max(1, v), totalPages); state.page = v; renderTable(); });
      const ofSpan = document.createElement('span'); ofSpan.className='small'; ofSpan.textContent = ` / ${totalPages}`;
      pagerDiv.appendChild(btnPrev); pagerDiv.appendChild(pageInfo); pagerDiv.appendChild(pageInput); pagerDiv.appendChild(ofSpan); pagerDiv.appendChild(btnNext);
    }

    // render table (core)
    function renderTable() {
      const filtered = applyFiltersAndSort_internal();
      const total = filtered.length;
      const totalPages = Math.max(1, Math.ceil(total / state.pageLength));
      if (state.page > totalPages) state.page = totalPages;
      const start = (state.page - 1) * state.pageLength;
      const pageRows = filtered.slice(start, start + state.pageLength);

      // Build a proportional colgroup using relative_col_width (fallback to 1)
      const vcols = visibleColsArr();
      const totalWeight = vcols.reduce((s,c) => s + (Number(c.relative_col_width) > 0 ? Number(c.relative_col_width) : 1), 0);

      const table = document.createElement('table');

      const colgroup = document.createElement('colgroup');
      vcols.forEach(c => {
        const colEl = document.createElement('col');
        const weight = Number(c.relative_col_width) > 0 ? Number(c.relative_col_width) : 1;
        colEl.style.width = (100 * (weight / totalWeight)).toFixed(3) + '%';
        colgroup.appendChild(colEl);
      });
      table.appendChild(colgroup);

      const thead = document.createElement('thead');
      const tr = document.createElement('tr');
      vcols.forEach(c => {
        const th = document.createElement('th');
        th.textContent = c.title ?? c.key;
        const filterKeyForMark = c.key === '__stats__' ? '__stats__' : c.key;
        if (state.columnFilters.has(filterKeyForMark)) th.classList.add('filtered'); else th.classList.remove('filtered');
        const span = document.createElement('span'); span.className='sort-ind'; if (state.sortKey === c.key) span.textContent = state.sortDir === 1 ? '▲' : '▼';
        th.appendChild(span);
        // sorting
        th.addEventListener('click', () => {
          if (state.sortKey === c.key) state.sortDir = -state.sortDir;
          else { state.sortKey = c.key; state.sortDir = 1; }
          state.page = 1; renderTable();
        });
        // contextmenu to open filter if filter_type is provided
        const isFilterable = (c.filterable === false) ? false : (c.filter_type != null || c.key === '__stats__');
        if (isFilterable) {
          th.addEventListener('contextmenu', (ev) => { ev.preventDefault(); openFilterDropdownForColumn(c, th); });
        } else {
          th.title = 'Filtering disabled for this column';
        }
        tr.appendChild(th);
      });
      thead.appendChild(tr); table.appendChild(thead);

      const tbody = document.createElement('tbody');
      if (pageRows.length === 0) {
        const tr0=document.createElement('tr'); const td0=document.createElement('td'); td0.colSpan = Math.max(vcols.length,1); td0.className='no-data'; td0.textContent='No rows'; tr0.appendChild(td0); tbody.appendChild(tr0);
      } else {
        pageRows.forEach(row => {
          const r = document.createElement('tr');
          vcols.forEach(c => {
            const td = document.createElement('td');
            if (c.key === '__stats__') {
              const min = getValue(row,'min'), max = getValue(row,'max'), avg = getValue(row,'avg'), sum = getValue(row,'sum');
              const parts = []; // initialize list
              if (min != null & min !== '') {
                const minS = fmtNumberDisplay(min)
                parts.push(`Min: <strong>${minS}</strong>`)
              }
              if (max != null & max !== '') {
                const maxS = fmtNumberDisplay(max)
                parts.push(`Max: <strong>${maxS}</strong>`)
              }
              if (avg != null & avg !== '') {
                const avgS = fmtNumberDisplay(avg)
                parts.push(`Avg: <strong>${avgS}</strong>`)
              }
              if (sum != null & sum !== '') {
                const sumS = fmtNumberDisplay(sum)
                parts.push(`Sum: <strong>${sumS}</strong>`)
              }

              if (parts.length === 0) {
                td.textContent = '';
              } else {
                td.innerHTML = parts.join('<br>')
              }

            } else if (c.collapse) {
              const raw = getValue(row, c.key);
              const descEl = makeDescriptionCell(raw);
              td.innerHTML = '';
              td.appendChild(descEl);
            } else {
              const raw = getValue(row, c.key);
              if (c.link && raw != null && raw !== '') {
                const a = document.createElement('a'); a.className='cell-link'; a.href = String(raw); a.target='_blank'; a.rel='noopener noreferrer';
                a.textContent = String(raw);
                a.title = String(raw);
                td.appendChild(a);
                td.title = String(raw);
              } else if (c.filter_type === 'number' || (typeof raw === 'number')) {
                const v = raw == null || raw === '' ? '' : fmtNumberDisplay(raw);
                td.textContent = v;
                td.classList.add('dt-right');
                if (v) td.title = String(v);
              } else if (Array.isArray(raw)) {
                const joined = raw.join(', ');
                td.textContent = joined;
                if (joined) td.title = joined;
              } else {
                const txt = raw == null ? '' : String(raw);
                td.textContent = txt;
                if (txt) td.title = txt;
              }
            }
            r.appendChild(td);
          });
          tbody.appendChild(r);
        });
      }
      table.appendChild(tbody);
      tableArea.innerHTML = ''; tableArea.appendChild(table);
      renderPager(filtered.length, Math.max(1, Math.ceil(filtered.length / state.pageLength)));

      // Publish visible dataset_id keys if configured
      if (cfg.publishesVisibleKeys) {
        const visibleKeys = new Set(applyFiltersAndSort_internal().map(r => String(getValue(r,'dataset_id'))));
        TABLE_REGISTRY.forEach(entry => {
          if (entry.cfg.linkFrom === cfg.id && typeof entry.instance.receiveExternalKeyFilter === 'function') {
            entry.instance.receiveExternalKeyFilter(visibleKeys, cfg.id);
          }
        });
      }
    } // end renderTable

    // Expose API & register
    const exported = {
      cfg,
      renderTable,
      receiveExternalKeyFilter,
      applyFiltersAndSort: applyFiltersAndSort_internal,
      instanceState: state,
      clearFilters: () => {
        state.columnFilters.clear();
        state.externalKeyFilter = null;
        state.externalKeyFilterFromLinkedTable = null;
        state._effectiveExternalKeyFilter = null;
        state.page = 1;
        renderTable();
      }
    };
    TABLE_REGISTRY.set(cfg.id, { cfg, instance: exported });

    // defaults
    state.sortKey = 'dataset_id';
    state.sortDir = 1;

    // initial render
    renderTable();
    return exported;
  } // end buildTable

  (async function initAll(){
    const container = document.getElementById('tables-container');
    for (const cfg of TABLES) {
      await buildTable(cfg, container);
    }

    // simplified bidirectional syncing using internal applyFiltersAndSort
    const t1 = TABLE_REGISTRY.get('table1');
    const t2 = TABLE_REGISTRY.get('table2');
    if (t1 && t2) {
      const origRender1 = t1.instance.renderTable.bind(t1.instance);
      t1.instance.renderTable = function() {
        origRender1();
        const visible = new Set(t1.instance.applyFiltersAndSort().map(r => String(getValue(r,'dataset_id'))));
        if (t2.instance && typeof t2.instance.receiveExternalKeyFilter === 'function') {
          t2.instance.receiveExternalKeyFilter(visible, 'table1');
        }
      };
      const origRender2 = t2.instance.renderTable.bind(t2.instance);
      t2.instance.renderTable = function() {
        origRender2();
        const visible = new Set(t2.instance.applyFiltersAndSort().map(r => String(getValue(r,'dataset_id'))));
        if (t1.instance && typeof t1.instance.receiveExternalKeyFilter === 'function') {
          t1.instance.receiveExternalKeyFilter(visible, 'table2');
        }
      };
    }

    // Initial render + sync
    TABLE_REGISTRY.forEach(entry => {
      if (entry && entry.instance && typeof entry.instance.renderTable === 'function') entry.instance.renderTable();
    });

  })();