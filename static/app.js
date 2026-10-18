// Progressive enhancement: the core app works even without JavaScript.
document.addEventListener('DOMContentLoaded', () => {
  const search = document.querySelector('#club-search');
  const count = document.querySelector('#club-search-count');
  if (search && count) {
    const cards = Array.from(document.querySelectorAll('[data-search]'));
    function filterClubs() {
      const query = search.value.trim().toLocaleLowerCase();
      let visible = 0;
      cards.forEach((card) => {
        const match = card.dataset.search.includes(query);
        card.hidden = !match;
        if (match) visible++;
      });
      count.textContent = `${visible} club${visible === 1 ? '' : 's'} found`;
    }
    search.addEventListener('input', filterClubs);
    filterClubs();
  }
});
