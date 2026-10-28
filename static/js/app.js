// Дані приходять із сервера, тому спочатку масив порожній
let items = [];

const tbody = document.querySelector('#groups-body');
const form = document.querySelector('#group-form');
const message = document.querySelector('#message');

// Побудова таблиці з масиву
function renderTable() {
  tbody.innerHTML = '';

  items.forEach(function (item) {
    const row = document.createElement('tr');

    const nameCell = document.createElement('td');
    nameCell.textContent = item.name;

    const foundedCell = document.createElement('td');
    foundedCell.textContent = item.founded;

    const ideologyCell = document.createElement('td');
    ideologyCell.textContent = item.ideology;

    const lastActionCell = document.createElement('td');
    lastActionCell.textContent = item.last_action || '—';

    const activeCell = document.createElement('td');
    activeCell.textContent = item.active ? 'так' : 'ні';

    const targetsCell = document.createElement('td');
    targetsCell.textContent = item.targets.join(', ') || '—';

    const actionCell = document.createElement('td');
    const deleteButton = document.createElement('button');
    deleteButton.textContent = 'Видалити';
    deleteButton.dataset.id = item.id;
    actionCell.append(deleteButton);

    row.append(nameCell, foundedCell, ideologyCell, lastActionCell,
               activeCell, targetsCell, actionCell);
    tbody.append(row);
  });
}

// Завантаження списку з сервера
async function loadItems() {
  try {
    const response = await fetch('/api/groups');
    items = await response.json();
    renderTable();
  } catch (error) {
    message.textContent = 'Сервер недоступний';
  }
}

// Додавання запису через сервер
form.addEventListener('submit', async function (event) {
  event.preventDefault();

  const name = document.querySelector('#name').value.trim();
  const founded = Number(document.querySelector('#founded').value);
  const ideology = document.querySelector('#ideology').value;
  const lastAction = document.querySelector('#lastAction').value;
  const active = document.querySelector('#active').checked;

  message.textContent = '';

  if (name === '') {
    message.textContent = 'Вкажіть назву угруповання';
    return;
  }

  if (founded < 1970 || founded > 2026) {
    message.textContent = 'Рік заснування має бути від 1970 до 2026';
    return;
  }

  if (lastAction === '') {
    message.textContent = 'Вкажіть дату останньої відомої акції';
    return;
  }

  const newItem = {
    name: name,
    founded: founded,
    ideology: ideology,
    last_action: lastAction,
    active: active
  };

  try {
    const response = await fetch('/api/groups', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newItem)
    });
    if (!response.ok) {
      const error = await response.json();
      message.textContent = error.error;
      return;
    }
    const created = await response.json();
    items.push(created);
    renderTable();
    form.reset();
    message.textContent = 'Запис додано';
  } catch (error) {
    message.textContent = 'Сервер недоступний';
  }
});

// Видалення: один обробник на все тіло таблиці
tbody.addEventListener('click', async function (event) {
  const id = event.target.dataset.id;
  if (!id) {
    return;
  }

  try {
    const response = await fetch('/api/groups/' + id, { method: 'DELETE' });
    if (!response.ok) {
      message.textContent = 'Не вдалося видалити запис';
      return;
    }
    items = items.filter(item => item.id !== Number(id));
    renderTable();
    message.textContent = 'Запис видалено';
  } catch (error) {
    message.textContent = 'Сервер недоступний';
  }
});

loadItems();
