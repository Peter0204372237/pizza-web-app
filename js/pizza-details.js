(async function () {
    "use strict";

    const params = new URLSearchParams(window.location.search);
    const slug = params.get("pizza");
    const details = document.getElementById("pizza-details-content");
    const notFound = document.getElementById("pizza-not-found");

    if (!slug) {
        notFound.hidden = false;
        return;
    }

    try {
        const response = await fetch("/api/pizzas/" + encodeURIComponent(slug) + "/");
        if (!response.ok) {
            if (response.status === 404) {
                throw new Error("That pizza is not currently available. Please choose another pizza from the menu.");
            }
            throw new Error("The menu service returned an error (" + response.status + "). Please try again.");
        }
        const pizza = await response.json();
        details.hidden = false;
        document.title = `${pizza.name} — Customize Your Pizza | PizzaSlice`;
        document.getElementById("pizza-name").textContent = pizza.name;
        document.getElementById("pizza-image").src = pizza.image;
        document.getElementById("pizza-image").alt = `${pizza.name} pizza`;
        document.getElementById("pizza-category").textContent = pizza.category;
        document.getElementById("pizza-description").textContent = pizza.description;
        document.getElementById("pizza-ingredients").textContent = pizza.ingredients.join(", ");

        const sizePrices = Object.fromEntries(
            Object.entries(pizza.prices).map(function (entry) {
                return [entry[0], Number(entry[1])];
            })
        );
        document.querySelectorAll('input[name="size"]').forEach(function (input) {
            const price = sizePrices[input.value];
            input.parentElement.querySelector("small").textContent = `GH₵${price}`;
        });

        const removableOptions = document.getElementById("removable-options");
        pizza.ingredients.forEach(function (ingredient) {
            const label = document.createElement("label");
            const checkbox = document.createElement("input");
            const text = document.createElement("span");

            checkbox.type = "checkbox";
            checkbox.name = "remove";
            checkbox.value = ingredient;
            text.textContent = ingredient;
            label.append(checkbox, text);
            removableOptions.append(label);
        });

        const form = document.getElementById("pizza-order-form");
        const priceOutput = document.getElementById("pizza-price");
        const orderMessage = document.getElementById("order-message");
        const quantityInput = document.getElementById("pizza-quantity");

        const getUnitPrice = function () {
            const size = form.elements.namedItem("size").value;
            const extras = form.querySelectorAll('input[name="extra"]:checked').length;
            const premiumCrust = form.elements.namedItem("crust").value !== "Original";

            return sizePrices[size] + extras * 3 + (premiumCrust ? 5 : 0);
        };

        const getTotal = function () {
            return getUnitPrice() * Number(quantityInput.value);
        };

        const updatePrice = function () {
            if (!quantityInput.validity.valid) {
                return;
            }

            priceOutput.textContent = `GH₵${getTotal()}`;
            orderMessage.textContent = "";
        };

        form.addEventListener("change", updatePrice);
        quantityInput.addEventListener("input", updatePrice);
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            if (!form.reportValidity()) {
                return;
            }

            const order = {
                slug: pizza.slug,
                pizza: pizza.name,
                image: pizza.image,
                quantity: Number(quantityInput.value),
                size: form.elements.namedItem("size").value,
                dough: form.elements.namedItem("dough").value,
                crust: form.elements.namedItem("crust").value,
                extraToppings: Array.from(
                    form.querySelectorAll('input[name="extra"]:checked'),
                    function (input) { return input.value; }
                ),
                removedIngredients: Array.from(
                    form.querySelectorAll('input[name="remove"]:checked'),
                    function (input) { return input.value; }
                ),
                unitPrice: getUnitPrice(),
                price: getTotal()
            };

            try {
                window.PizzaCart.add(order);
                orderMessage.classList.remove("order-error");
                orderMessage.textContent = `${order.quantity} × ${order.pizza} (${order.size}) added to your cart for GH₵${order.price}.`;
            } catch (error) {
                orderMessage.classList.add("order-error");
                orderMessage.textContent = error.message;
                console.error("Could not add pizza to cart.", error);
            }
        });
    } catch (error) {
        notFound.hidden = false;
        notFound.querySelector("h1").textContent = error instanceof TypeError
            ? "Could not connect to the menu service."
            : "Pizza details unavailable.";
        notFound.querySelector("p").textContent = error instanceof TypeError
            ? "Open this page through the Django server at http://127.0.0.1:8000, then refresh."
            : error.message;
        console.error("Could not load pizza details.", error);
    }
}());
