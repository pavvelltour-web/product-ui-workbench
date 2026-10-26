/* Native Workbench 0.1.1 — post-evaluation correction; original MIT source. */

export function el(tag, attributes = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attributes || {})) {
    if (value == null || (value === false && !key.startsWith('aria-'))) continue;
    if (key.startsWith('on') && typeof value === 'function') {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (key === 'className') node.className = value;
    else if (key === 'textContent') node.textContent = value;
    else if (['value', 'checked', 'disabled', 'hidden'].includes(key)) node[key] = value;
    else node.setAttribute(key, key.startsWith('aria-') ? String(value) : value === true ? '' : String(value));
  }
  const append = value => {
    if (Array.isArray(value)) value.forEach(append);
    else if (value != null && value !== false) node.append(value instanceof Node ? value : document.createTextNode(String(value)));
  };
  children.forEach(append);
  return node;
}

/** Uncontrolled selection controller; returns snapshots rather than its mutable internal Set. */
export function createSelectionModel(ids, options = {}) {
  const allowed = new Set(ids);
  const selected = new Set();
  const listeners = new Set(options.onChange ? [options.onChange] : []);
  const notify = () => listeners.forEach(callback => callback(new Set(selected)));
  return {
    get selected() { return new Set(selected); },
    get count() { return selected.size; },
    has(id) { return selected.has(id); },
    toggle(id) {
      if (!allowed.has(id)) throw new RangeError(`Unknown selection id: ${id}`);
      selected.has(id) ? selected.delete(id) : selected.add(id);
      notify();
      return selected.has(id);
    },
    clear() { if (selected.size) { selected.clear(); notify(); } },
    subscribe(callback) { listeners.add(callback); return () => listeners.delete(callback); }
  };
}

/** Native table: heading buttons sort values; keyboard uses native Tab/Enter/Space, no grid impersonation. */
export function createSortableTable({ columns, rows, initialKey = columns[0]?.key, caption = 'Comparison', onSort } = {}) {
  if (!Array.isArray(columns) || !columns.length || !Array.isArray(rows)) throw new TypeError('columns and rows are required');
  let data = [...rows];
  let sortKey = initialKey;
  let direction = 'ascending';
  if (!columns.some(column => column.key === sortKey)) throw new RangeError('initialKey must match a column');
  const body = el('tbody');
  const headers = new Map();
  const announcement = el('p', { className: 'wb-visually-hidden', role: 'status', 'aria-live': 'polite' });
  const headingRow = el('tr');
  function drawRows() {
    headers.forEach((heading, key) => heading.setAttribute('aria-sort', key === sortKey ? direction : 'none'));
    const column = columns.find(item => item.key === sortKey);
    const sorted = data.map((row, index) => ({ row, index })).sort((left, right) => {
      const a = column.value ? column.value(left.row) : left.row[sortKey];
      const b = column.value ? column.value(right.row) : right.row[sortKey];
      const order = typeof a === 'number' && typeof b === 'number' ? a - b : String(a ?? '').localeCompare(String(b ?? ''), undefined, { numeric: true });
      return (direction === 'ascending' ? order : -order) || left.index - right.index;
    });
    body.replaceChildren(...sorted.map(({ row }) => el('tr', {}, columns.map(item =>
      el('td', { className: item.numeric ? 'wb-number' : '' }, item.render ? item.render(row) : row[item.key] ?? '—')))));
    announcement.textContent = `Sorted by ${column.label}, ${direction}. ${data.length} rows.`;
  }
  for (const column of columns) {
    const button = el('button', { type: 'button', className: 'wb-sort', onclick: () => {
      direction = sortKey === column.key && direction === 'ascending' ? 'descending' : 'ascending';
      sortKey = column.key;
      drawRows();
      onSort?.({ key: sortKey, direction });
    } }, column.label, el('span', { 'aria-hidden': 'true', className: 'wb-sort-marker' }, ' ↕'));
    const heading = el('th', { scope: 'col', 'aria-sort': 'none' }, button);
    headers.set(column.key, heading);
    headingRow.append(heading);
  }
  const table = el('table', { className: 'wb-table' }, el('caption', {}, caption), el('thead', {}, headingRow), body);
  const root = el('div', { className: 'wb-table-region', tabindex: '0', role: 'region', 'aria-label': caption }, table, announcement);
  root.setRows = nextRows => { data = [...nextRows]; drawRows(); };
  root.getSort = () => ({ key: sortKey, direction });
  drawRows();
  return root;
}

/** List/detail with independent item buttons, restored focus on Back and supplied detail renderer. */
export function createListDetail({ items, getLabel = item => item.label, renderDetail, onOpen, label = 'Items' } = {}) {
  if (!Array.isArray(items) || typeof renderDetail !== 'function') throw new TypeError('items and renderDetail are required');
  let data = [...items];
  let currentId = null;
  let originButton = null;
  const list = el('ul', { className: 'wb-list' });
  const region = el('section', { className: 'wb-detail', tabindex: '-1', 'aria-label': `${label} detail`, hidden: true });
  const content = el('div');
  const back = el('button', { type: 'button', className: 'wb-button', onclick: () => {
    currentId = null;
    region.hidden = true;
    content.replaceChildren();
    list.querySelectorAll('[aria-current]').forEach(button => button.removeAttribute('aria-current'));
    originButton?.focus();
  } }, 'Back to list');
  region.append(back, content);
  function open(item, button) {
    currentId = item.id;
    originButton = button;
    list.querySelectorAll('[aria-current]').forEach(candidate => candidate.removeAttribute('aria-current'));
    button.setAttribute('aria-current', 'true');
    content.replaceChildren(renderDetail(item));
    region.hidden = false;
    region.focus();
    onOpen?.(item);
  }
  function draw() {
    list.replaceChildren(...data.map(item => {
      const button = el('button', { type: 'button', className: 'wb-list-button' }, getLabel(item));
      button.addEventListener('click', () => open(item, button));
      return el('li', {}, button);
    }));
  }
  const root = el('div', { className: 'wb-list-detail' }, el('nav', { 'aria-label': label }, list), region);
  root.getCurrentId = () => currentId;
  root.setItems = next => { data = [...next]; currentId = null; region.hidden = true; draw(); };
  draw();
  return root;
}

/** Staged form with optional local drafts and async save recovery. Stores only explicitly supplied fixture values. */
export function createRecoveryForm({ id = 'recovery', steps, initialValues = {}, storage = null, storageKey = null, onSave } = {}) {
  if (!Array.isArray(steps) || !steps.length || typeof onSave !== 'function') throw new TypeError('steps and onSave are required');
  const names = steps.flatMap(step => step.fields.map(field => field.name));
  if (new Set(names).size !== names.length) throw new RangeError('Field names must be unique');
  const supportedTypes = new Set(['text','textarea','email','url','tel','search','number','date','time','datetime-local','month','week','checkbox']);
  const definitions = steps.flatMap(step => step.fields);
  for (const field of definitions) {
    if (!supportedTypes.has(field.type || 'text')) throw new TypeError(`Unsupported recovery field type: ${field.type}`);
  }
  const values = { ...initialValues };
  for (const field of definitions) if (field.type === 'checkbox') values[field.name] = values[field.name] === true;
  let stepIndex = 0;
  let state = 'editing';
  let storageProblem = '';
  if (storage && storageKey) {
    try {
      const raw = storage.getItem(storageKey);
      if (raw) {
        const saved = JSON.parse(raw);
        if (saved.version === 1 && saved.values && typeof saved.values === 'object') {
          for (const field of definitions) if (Object.hasOwn(saved.values, field.name)) {
            const value = saved.values[field.name];
            if (field.type === 'checkbox' ? typeof value === 'boolean' : typeof value === 'string' || typeof value === 'number') values[field.name] = value;
            else storageProblem = 'Some local draft fields could not be restored. Review their values.';
          }
        }
      }
    } catch { storageProblem = 'Local draft could not be loaded. You can still edit.'; }
  }
  const heading = el('h2');
  const fields = el('div', { className: 'wb-fields' });
  const status = el('p', { role: 'status', 'aria-live': 'polite', className: 'wb-status' });
  const previous = el('button', { type: 'button', className: 'wb-button', onclick: () => {
    if (state === 'saving') return;
    stepIndex--; draw(); heading.focus();
  } }, 'Previous');
  const next = el('button', { type: 'submit', className: 'wb-button wb-primary' });
  const form = el('form', { className: 'wb-recovery-form' }, heading, fields, status, el('div', { className: 'wb-actions' }, previous, next));
  function draft() {
    if (!storage || !storageKey) return;
    try { storage.setItem(storageKey, JSON.stringify({ version: 1, values })); }
    catch { storageProblem = 'Local draft could not be stored. Keep this page open until saved.'; status.textContent = storageProblem; }
  }
  function draw() {
    heading.textContent = `${stepIndex + 1} of ${steps.length}: ${steps[stepIndex].label}`;
    heading.tabIndex = -1;
    fields.replaceChildren(...steps[stepIndex].fields.map(field => {
      const inputId = `${id}-${field.name}`;
      const input = el(field.type === 'textarea' ? 'textarea' : 'input', {
        id: inputId, name: field.name, type: field.type === 'textarea' ? null : field.type || 'text',
        required: !!field.required, value: field.type === 'checkbox' ? null : values[field.name] ?? '', checked: field.type === 'checkbox' ? values[field.name] === true : null, className: field.type === 'checkbox' ? 'wb-checkbox' : 'wb-input',
        oninput: event => { values[field.name] = field.type === 'checkbox' ? event.target.checked : event.target.value; state = 'editing'; draft(); }
      });
      return el('div', { className: 'wb-field' }, el('label', { for: inputId }, field.label), input,
        field.hint ? el('p', { className: 'wb-hint', id: `${inputId}-hint` }, field.hint) : null);
    }));
    fields.querySelectorAll('.wb-field').forEach(field => {
      const hint = field.querySelector('.wb-hint');
      if (hint) field.querySelector('input,textarea').setAttribute('aria-describedby', hint.id);
    });
    previous.hidden = stepIndex === 0;
    previous.disabled = state === 'saving';
    next.disabled = state === 'saving';
    next.textContent = state === 'saving' ? 'Saving…' : stepIndex < steps.length - 1 ? 'Continue' : state === 'save-error' ? 'Retry save' : 'Save';
    status.textContent = storageProblem;
  }
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (state === 'saving' || !form.reportValidity()) return;
    if (stepIndex < steps.length - 1) { stepIndex++; draft(); draw(); heading.focus(); return; }
    state = 'saving';
    previous.disabled = true; next.disabled = true; next.textContent = 'Saving…';
    fields.querySelectorAll('input,textarea').forEach(input => { input.disabled = true; });
    status.textContent = 'Saving changes…';
    try {
      await onSave({ ...values });
      state = 'saved';
      if (storage && storageKey) {
        try { storage.removeItem(storageKey); }
        catch { storageProblem = 'Saved, but the old local draft could not be cleared.'; }
      }
      status.textContent = storageProblem || 'Saved successfully.';
    } catch (error) {
      state = 'save-error';
      draft();
      status.textContent = `Save failed. Your edits are still here. ${error?.message || 'Try again.'}`;
    } finally {
      previous.disabled = false; next.disabled = false;
      fields.querySelectorAll('input,textarea').forEach(input => { input.disabled = false; });
      next.textContent = state === 'save-error' ? 'Retry save' : 'Save';
    }
  });
  form.getState = () => ({ step: stepIndex, status: state, values: { ...values }, storageProblem });
  form.resetDraft = () => {
    if (state === 'saving') return false;
    if (storage && storageKey) { try { storage.removeItem(storageKey); } catch { return false; } }
    names.forEach(name => { delete values[name]; });
    Object.assign(values, initialValues);
    for (const field of definitions) if (field.type === 'checkbox') values[field.name] = values[field.name] === true;
    stepIndex = 0; state = 'editing'; storageProblem = ''; draw(); return true;
  };
  draw();
  return form;
}
