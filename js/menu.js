(function () {
    "use strict";

    const feedback = document.getElementById("menu-cart-message");
    const grid = document.getElementById("menu-grid");
    const filters = document.getElementById("menu-filters");
    const template = document.getElementById("menu-card-template");
    const emptyMessage = document.getElementById("menu-empty");
    const countOutput = document.getElementById("menu-count");
    const query = new URLSearchParams(window.location.search)
        .get("query")
        ?.trim()
        .toLocaleLowerCase() || "";
    const menuFilters = [
        { name: "All", slug: null },
        { name: "Pizza", slug: "pizza" },
        { name: "Loaded Fries", slug: "loaded-fries" },
        { name: "Drinks", slug: "drinks" },
        { name: "Weekend Promo", slug: "weekend-promo" },
        { name: "Combo", slug: "combo" }
    ];
    let pizzas = [];
    let menuItems = [];
    let menuItemCategorySlugs = new Set();
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
                    if (choice.dataset.productType === "menu-item") {
                        return item.productType === "menu_item" &&
                            item.menuItemSlug === choice.dataset.slug;
                    }
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
        const totalItems = pizzas.length + menuItems.length;

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
        if (selectedCategory && selectedCategory !== "pizza") {
            const category = menuFilters.find(function (category) {
                return category.slug === selectedCategory;
            });
            const categoryName = category ? category.name : "menu";
            countOutput.textContent = visibleCount + " " +
                categoryName.toLocaleLowerCase() + (visibleCount === 1 ? " item shown" : " items shown");
            emptyMessage.textContent = "No items in this category yet. Check back soon.";
        } else {
            countOutput.textContent = selectedCategory === "pizza"
                ? visibleCount + (visibleCount === 1 ? " pizza shown" : " pizzas shown")
                : query
                    ? visibleCount + (visibleCount === 1 ? " item shown" : " items shown")
                    : totalItems + (totalItems === 1 ? " item · zero wrong choices" : " items · zero wrong choices");
            emptyMessage.textContent = selectedCategory === "pizza"
                ? "No pizzas match the selected category or search."
                : "No menu items match the selected category or search.";
        }
    }

    function renderFilters(categories) {
        categories.forEach(function (category) {
            if (!menuFilters.some(function (filter) {
                return filter.slug === category.slug;
            })) {
                menuFilters.push({ name: category.name, slug: category.slug });
            }
        });

        filters.replaceChildren();
        menuFilters.forEach(function (category) {
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

    function createMenuItemCard(item) {
        const card = template.content.firstElementChild.cloneNode(true);
        const link = card.querySelector(".menu-card-link");
        const image = card.querySelector(".menu-media img");
        const choice = card.querySelector(".pizza-choice");
        const choiceLabel = card.querySelector(".pizza-choice-button");

        link.remove();
        card.dataset.cat = item.category_slug;
        card.dataset.sourceCat = item.category_slug;
        card.dataset.search = [
            item.name,
            item.category,
            item.description
        ].join(" ").toLocaleLowerCase();
        card.querySelector(".menu-category").textContent = item.category;
        if (!grid.querySelector('[data-source-cat="' + item.category_slug + '"]')) {
            card.id = item.category_slug;
        }
        image.decoding = "async";
        image.src = item.image;
        image.alt = item.name;
        image.addEventListener("error", function () {
            image.style.display = "none";
            image.parentElement.classList.add("menu-media-error");
        });
        card.querySelector("h3").textContent = item.name;
        card.querySelector(".menu-body > p").textContent = item.description;
        card.querySelector(".menu-price").textContent = money(item.price);
        choice.id = "choose-menu-item-" + item.slug;
        choice.dataset.slug = item.slug;
        choice.dataset.productType = "menu-item";
        choiceLabel.htmlFor = choice.id;
        return card;
    }

    function createCard(pizza) {
        const card = template.content.firstElementChild.cloneNode(true);
        const link = card.querySelector(".menu-card-link");
        const image = card.querySelector(".menu-media img");
        const choice = card.querySelector(".pizza-choice");
        const choiceLabel = card.querySelector(".pizza-choice-button");

        card.dataset.cat = "pizza";
        card.dataset.sourceCat = pizza.category_slug;
        card.dataset.search = [
            pizza.name,
            pizza.category,
            pizza.description,
            pizza.ingredients.join(" ")
        ].join(" ").toLocaleLowerCase();
        card.querySelector(".menu-category").textContent = "Pizza";
        if (!grid.querySelector('[data-source-cat="' + pizza.category_slug + '"]')) {
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
        image.decoding = "async";
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
        choice.dataset.productType = "pizza";
        choiceLabel.htmlFor = choice.id;
        return card;
    }

    function renderCatalog(catalog, categories, items, itemCategories) {
        const categoriesBySlug = new Map();
        if (Array.isArray(categories)) {
            categories.forEach(function (category) {
                if (category && typeof category.name === "string" &&
                    typeof category.slug === "string") {
                    categoriesBySlug.set(category.slug, category);
                }
            });
        }

        const itemCategoriesBySlug = new Map();
        if (Array.isArray(itemCategories)) {
            itemCategories.forEach(function (category) {
                if (category && typeof category.name === "string" &&
                    typeof category.slug === "string") {
                    itemCategoriesBySlug.set(category.slug, category);
                }
            });
        }

        if (!Array.isArray(categories) || categoriesBySlug.size !== categories.length ||
            !Array.isArray(itemCategories) ||
            itemCategoriesBySlug.size !== itemCategories.length ||
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
        }) || !Array.isArray(items) || items.some(function (item) {
            return !item || typeof item.slug !== "string" ||
                typeof item.name !== "string" ||
                typeof item.category !== "string" ||
                typeof item.category_slug !== "string" ||
                !categoriesBySlug.has(item.category_slug) ||
                !itemCategoriesBySlug.has(item.category_slug) ||
                typeof item.description !== "string" ||
                typeof item.image !== "string" ||
                !Number.isFinite(Number(item.price)) ||
                Number(item.price) < 0;
        })) {
            throw new Error("The menu data from the server is invalid.");
        }

        pizzas = catalog;
        menuItems = items;
        menuItemCategorySlugs = new Set(itemCategoriesBySlug.keys());
        const hashCategory = decodeURIComponent(window.location.hash.slice(1));
        itemCategories.forEach(function (category) {
            if (!menuFilters.some(function (filter) {
                return filter.slug === category.slug;
            })) {
                menuFilters.push({ name: category.name, slug: category.slug });
            }
        });
        const isMenuFilter = menuFilters.some(function (category) {
            return category.slug === hashCategory;
        });
        selectedCategory = isMenuFilter
            ? hashCategory
            : menuItemCategorySlugs.has(hashCategory)
                ? hashCategory
            : categoriesBySlug.has(hashCategory)
                ? "pizza"
                : null;
        renderFilters(itemCategories);
        grid.replaceChildren();
        catalog.forEach(function (pizza) {
            const card = createCard(pizza);
            grid.append(card);
        });
        items.forEach(function (item) {
            const card = createMenuItemCard(item);
            grid.append(card);
        });
        grid.setAttribute("aria-busy", "false");
        refreshChoices();
        applyFilters();
        if (menuItemCategorySlugs.has(hashCategory)) {
            grid.querySelector('[data-source-cat="' + hashCategory + '"]')?.scrollIntoView();
        } else if (categoriesBySlug.has(hashCategory)) {
            grid.querySelector('[data-source-cat="' + hashCategory + '"]')?.scrollIntoView();
        } else if (selectedCategory === "pizza") {
            grid.querySelector('[data-cat="pizza"]')?.scrollIntoView();
        } else if (hashCategory === "hot-honey") {
            grid.querySelector("#hot-honey")?.scrollIntoView();
        }
    }

    grid.addEventListener("change", function (event) {
        const choice = event.target.closest(".pizza-choice");
        if (!choice) {
            return;
        }
        if (choice.dataset.productType === "menu-item") {
            const item = menuItems.find(function (menuItem) {
                return menuItem.slug === choice.dataset.slug;
            });
            if (!item) {
                choice.checked = false;
                feedback.textContent = "That item is no longer available. Refresh the menu and try again.";
                feedback.classList.add("cart-error");
                return;
            }

            try {
                if (choice.checked) {
                    window.PizzaCart.add({
                        productType: "menu_item",
                        menuItemSlug: item.slug,
                        pizza: item.name,
                        image: item.image,
                        quantity: 1,
                        unitPrice: Number(item.price)
                    });
                    feedback.textContent = item.name + " added to your cart.";
                } else {
                    const items = window.PizzaCart.getItems();
                    const index = items.findIndex(function (cartItem) {
                        return cartItem.productType === "menu_item" &&
                            cartItem.menuItemSlug === item.slug;
                    });
                    if (index !== -1) {
                        window.PizzaCart.remove(index);
                    }
                    feedback.textContent = item.name + " removed from your cart.";
                }
                feedback.classList.remove("cart-error");
            } catch (error) {
                choice.checked = !choice.checked;
                feedback.textContent = error.message || "We couldn’t update your cart. Please try again.";
                feedback.classList.add("cart-error");
                console.error("Could not update cart from menu.", error);
            }
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
                    productType: "pizza",
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
            renderCatalog(
                data.pizzas,
                data.categories,
                data.menu_items,
                data.menu_item_categories
            );
        })
        .catch(function (error) {
            grid.setAttribute("aria-busy", "false");
            countOutput.textContent = "Menu unavailable";
            feedback.textContent = error.message || "We couldn’t load the menu. Please refresh and try again.";
            feedback.classList.add("cart-error");
            console.error("Could not load menu.", error);
        });
}());
