(function () {
    "use strict";

    const feedback = document.getElementById("menu-cart-message");
    const grid = document.getElementById("menu-grid");
    const filters = document.getElementById("menu-filters");
    const template = document.getElementById("pizza-card-template");
    const emptyMessage = document.getElementById("menu-empty");
    const countOutput = document.getElementById("menu-count");
    const query = new URLSearchParams(window.location.search)
        .get("query")
        ?.trim()
        .toLocaleLowerCase() || "";
    let pizzas = [];
    let selectedCategory = null;

    function showLoading() {
        grid.replaceChildren();
        for (let index = 0; index < 6; index += 1) {
            const skeleton = document.createElement("div");
            skeleton.className = "menu-card-loading";
            skeleton.setAttribute("aria-hidden", "true");
            grid.append(skeleton);
        }
    }

    showLoading();

    function money(value) {
        return "GH₵" + Number(value);
    }

    function isQuickAdd(item, slug) {
        return item.slug === slug &&
            item.size === "S" &&
            item.dough === "Classic" &&
            item.crust === "Original" &&
            (!item.extraToppings || item.extraToppings.length === 0) &&
            (!item.removedIngredients || item.removedIngredients.length === 0);
    }

    function refreshChoices() {
        try {
            const items = window.PizzaCart.getItems();
            grid.querySelectorAll(".pizza-choice").forEach(function (choice) {
                choice.checked = items.some(function (item) {
                    return isQuickAdd(item, choice.dataset.slug);
                });
            });
        } catch (error) {
            feedback.textContent = "Your saved cart could not be read. Please check your browser’s saved site data.";
            feedback.classList.add("cart-error");
            console.error("Could not sync menu cart buttons.", error);
        }
    }

    function applyFilters() {
        let visibleCount = 0;

        grid.querySelectorAll(".menu-card").forEach(function (card) {
            const categoryMatches = selectedCategory === null ||
                card.dataset.cat === selectedCategory;
            const searchMatches = !query || card.dataset.search.includes(query);
            card.hidden = !categoryMatches || !searchMatches;
            if (!card.hidden) {
                visibleCount += 1;
            }
        });

        emptyMessage.hidden = visibleCount > 0;
        countOutput.textContent = query || selectedCategory !== null
            ? visibleCount + (visibleCount === 1 ? " pizza shown" : " pizzas shown")
            : pizzas.length + (pizzas.length === 1 ? " pizza · zero wrong choices" : " pizzas · zero wrong choices");
    }

    function renderFilters(categories) {
        filters.replaceChildren();
        const allCategories = [{ name: "All", slug: null }].concat(categories);
        allCategories.forEach(function (category) {
            const button = document.createElement("button");
            button.type = "button";
            button.dataset.category = category.slug || "";
            button.textContent = category.name;
            button.setAttribute(
                "aria-pressed",
                String(category.slug === selectedCategory)
            );
            filters.append(button);
        });

        filters.addEventListener("click", function (event) {
            const button = event.target.closest("button[data-category]");
            if (!button) {
                return;
            }
            selectedCategory = button.dataset.category || null;
            filters.querySelectorAll("button[data-category]").forEach(function (filter) {
                filter.setAttribute(
                    "aria-pressed",
                    String((filter.dataset.category || null) === selectedCategory)
                );
            });
            applyFilters();
        });
    }

    function createCard(pizza) {
        const card = template.content.firstElementChild.cloneNode(true);
        const link = card.querySelector(".menu-card-link");
        const image = card.querySelector(".menu-media img");
        const choice = card.querySelector(".pizza-choice");
        const choiceLabel = card.querySelector(".pizza-choice-button");

        card.dataset.cat = pizza.category_slug;
        card.dataset.search = [
            pizza.name,
            pizza.category,
            pizza.description,
            pizza.ingredients.join(" ")
        ].join(" ").toLocaleLowerCase();
        card.querySelector(".menu-category").textContent = pizza.category;
        if (!grid.querySelector('[data-cat="' + pizza.category_slug + '"]')) {
            card.id = pizza.category_slug;
        }
        if (pizza.slug === "hot-honey-salami") {
            const anchor = document.createElement("span");
            anchor.id = "hot-honey";
            anchor.className = "menu-card-anchor";
            card.append(anchor);
        }
        link.href = "pizza-details.html?pizza=" + encodeURIComponent(pizza.slug);
        link.setAttribute("aria-label", "Customize " + pizza.name);
        image.src = pizza.image;
        image.alt = pizza.name + " pizza";
        image.addEventListener("error", function () {
            image.style.display = "none";
            image.parentElement.classList.add("menu-media-error");
        });
        card.querySelector("h3").textContent = pizza.name;
        card.querySelector(".menu-body > p").textContent = pizza.description;
        card.querySelector(".menu-price").textContent = money(pizza.prices.S);
        choice.id = "choose-" + pizza.slug;
        choice.dataset.slug = pizza.slug;
        choiceLabel.htmlFor = choice.id;
        return card;
    }

    function renderCatalog(catalog, categories) {
        const categoriesBySlug = new Map();
        if (Array.isArray(categories)) {
            categories.forEach(function (category) {
                if (category && typeof category.name === "string" &&
                    typeof category.slug === "string") {
                    categoriesBySlug.set(category.slug, category);
                }
            });
        }

        if (!Array.isArray(categories) || categoriesBySlug.size !== categories.length ||
            !Array.isArray(catalog) || catalog.some(function (pizza) {
            return !pizza || typeof pizza.slug !== "string" ||
                typeof pizza.name !== "string" ||
                typeof pizza.category !== "string" ||
                typeof pizza.category_slug !== "string" ||
                !categoriesBySlug.has(pizza.category_slug) ||
                typeof pizza.description !== "string" ||
                !Array.isArray(pizza.ingredients) ||
                pizza.ingredients.some(function (ingredient) {
                    return typeof ingredient !== "string";
                }) ||
                !pizza.prices || typeof pizza.prices.S === "undefined";
        })) {
            throw new Error("The menu data from the server is invalid.");
        }

        pizzas = catalog;
        const hashCategory = decodeURIComponent(window.location.hash.slice(1));
        selectedCategory = categoriesBySlug.has(hashCategory) ? hashCategory : null;
        renderFilters(categories);
        grid.replaceChildren();
        catalog.forEach(function (pizza) {
            const card = createCard(pizza);
            grid.append(card);
        });
        refreshChoices();
        applyFilters();
        if (selectedCategory !== null) {
            grid.querySelector('[data-cat="' + selectedCategory + '"]')?.scrollIntoView();
        } else if (hashCategory === "hot-honey") {
            grid.querySelector("#hot-honey")?.scrollIntoView();
        }
    }

    grid.addEventListener("change", function (event) {
        const choice = event.target.closest(".pizza-choice");
        if (!choice) {
            return;
        }
        const pizza = pizzas.find(function (item) {
            return item.slug === choice.dataset.slug;
        });
        if (!pizza) {
            choice.checked = false;
            feedback.textContent = "That pizza is no longer available. Refresh the menu and try again.";
            feedback.classList.add("cart-error");
            return;
        }

        try {
            if (choice.checked) {
                window.PizzaCart.add({
                    slug: pizza.slug,
                    pizza: pizza.name,
                    image: pizza.image,
                    quantity: 1,
                    size: "S",
                    dough: "Classic",
                    crust: "Original",
                    extraToppings: [],
                    removedIngredients: [],
                    price: Number(pizza.prices.S)
                });
                feedback.textContent = pizza.name + " added to your cart.";
            } else {
                const items = window.PizzaCart.getItems();
                const index = items.findIndex(function (item) {
                    return isQuickAdd(item, pizza.slug);
                });
                if (index !== -1) {
                    window.PizzaCart.remove(index);
                }
                feedback.textContent = pizza.name + " removed from your cart.";
            }
            feedback.classList.remove("cart-error");
        } catch (error) {
            choice.checked = !choice.checked;
            feedback.textContent = error.message || "We couldn’t update your cart. Please try again.";
            feedback.classList.add("cart-error");
            console.error("Could not update cart from menu.", error);
        }
    });

    window.addEventListener("pizza-cart-updated", refreshChoices);
    fetch("/api/pizzas/")
        .then(function (response) {
            if (!response.ok) {
                throw new Error("The menu could not be loaded from the server.");
            }
            return response.json();
        })
        .then(function (data) {
            renderCatalog(data.pizzas, data.categories);
        })
        .catch(function (error) {
            countOutput.textContent = "Menu unavailable";
            feedback.textContent = error.message || "We couldn’t load the menu. Please refresh and try again.";
            feedback.classList.add("cart-error");
            console.error("Could not load menu.", error);
        });
}());
