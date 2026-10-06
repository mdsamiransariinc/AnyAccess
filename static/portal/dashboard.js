// Filtering remains local; Django has already removed unauthorized servers.
const searchInput = document.getElementById("server-search");
const cards = [...document.querySelectorAll("[data-search]")];
searchInput.addEventListener("input", () => {
  const query = searchInput.value.trim().toLowerCase();
  for (const card of cards) card.hidden = !card.dataset.search.includes(query);
  document.getElementById("search-empty").hidden = !cards.length || cards.some(card => !card.hidden);
});
