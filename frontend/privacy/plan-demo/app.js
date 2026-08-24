const scoreElement = document.querySelector('#initial-score');
const itemCountElement = document.querySelector('#item-count');
const summaryCountElement = document.querySelector('#summary-count');
const closingCountElement = document.querySelector('#closing-count');
const prioritySummary = document.querySelector('#priority-summary');
const itemsContainer = document.querySelector('#plan-items');
const itemTemplate = document.querySelector('#plan-item-template');
const summary = document.querySelector('.plan-summary');
const closing = document.querySelector('.plan-closing');
const errorMessage = document.querySelector('#plan-error');

const priorityOrder = ['Alta', 'Media', 'Baja'];

const renderPlanItem = (item, index) => {
  const fragment = itemTemplate.content.cloneNode(true);
  fragment.querySelector('.plan-item__number').textContent = index + 1;
  fragment.querySelector('.plan-item__code').textContent = item.control_code;
  fragment.querySelector('.plan-item__name').textContent = item.name;

  const priority = fragment.querySelector('.plan-item__priority');
  priority.textContent = `Prioridad ${item.priority.toLowerCase()}`;
  priority.dataset.priority = item.priority.toLowerCase();

  fragment.querySelector('.plan-item__finding').textContent = item.finding;
  fragment.querySelector('.plan-item__recommendation').textContent = item.recommendation;
  fragment.querySelector('.plan-item__validation p').textContent = item.validation_step;

  const steps = fragment.querySelector('.plan-item__steps');
  item.action_steps.forEach((step) => {
    const listItem = document.createElement('li');
    listItem.textContent = step;
    steps.append(listItem);
  });

  itemsContainer.append(fragment);
};

const renderPlan = (plan) => {
  scoreElement.textContent = `${plan.initial_score} / 100`;
  itemCountElement.textContent = plan.item_count;
  summaryCountElement.textContent = plan.item_count;
  closingCountElement.textContent = plan.item_count;

  const priorityCounts = plan.items.reduce((counts, item) => {
    counts[item.priority] = (counts[item.priority] || 0) + 1;
    return counts;
  }, {});

  priorityOrder.forEach((priority) => {
    const listItem = document.createElement('li');
    const count = priorityCounts[priority] || 0;
    listItem.innerHTML = `<strong>${count}</strong><span>prioridad ${priority.toLowerCase()}</span>`;
    prioritySummary.append(listItem);
  });

  plan.items.forEach(renderPlanItem);
  summary.hidden = false;
  closing.hidden = false;
};

fetch('fixture.json')
  .then((response) => {
    if (!response.ok) throw new Error('Fixture unavailable');
    return response.json();
  })
  .then(renderPlan)
  .catch(() => {
    errorMessage.hidden = false;
  });
