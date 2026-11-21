(function () {
    "use strict";

    const list = document.getElementById("cart-items");
    const empty = document.getElementById("cart-empty");
    const content = document.getElementById("cart-content");
    const subtotalOutput = document.getElementById("cart-subtotal");
    const countOutput = document.getElementById("cart-item-count");
    const message = document.getElementById("cart-message");
    let focusAfterRender = null;

    function money(value) {
        return "GH₵" + value.toFixed(2).replace(/\.00$/, "");
    }

    function restoreFocus(items) {
        if (!focusAfterRender) return;

        const focusTarget = focusAfterRender;
        focusAfterRender = null;
        if (focusTarget.action === "remove") {
            if (items.length) {
                const nextIndex = Math.min(focusTarget.index, items.length - 1);
                const nextRemove = list.querySelector(
                    '[data-cart-remove="' + nextIndex + '"]'
                );
                if (nextRemove) nextRemove.focus();
            } else {
                empty.querySelector(".cart-primary").focus();
            }
            return;
        }

        if (focusTarget.action === "step") {
            const selector = '[data-cart-index="' + focusTarget.index +
                '"][data-cart-quantity-step="' + focusTarget.step + '"]';
            const stepButton = list.querySelector(selector);
            if (stepButton && !stepButton.disabled) {
                stepButton.focus();
                return;
            }
        }

        const quantity = list.querySelector(
            '[data-cart-quantity="' + focusTarget.index + '"]'
        );
        if (quantity) quantity.focus();
    }

    function render() {
        let items;
        try {
            items = window.PizzaCart.getItems();
        } catch (error) {
            focusAfterRender = null;
            message.textContent = "We couldn’t load your cart. Please check your browser’s saved site data and try again.";
            message.classList.add("cart-error");
            console.error("Could not render the cart.", error);
            content.hidden = true;
            empty.hidden = true;
            return;
        }

        list.replaceChildren();
        message.textContent = "";
        message.classList.remove("cart-error");
        empty.hidden = items.length > 0;
        content.hidden = items.length === 0;

        if (!items.length) {
            restoreFocus(items);
            return;
        }

        let subtotal = 0;
        let count = 0;
        items.forEach(function (item, index) {
            subtotal += item.price;
            count += item.quantity;

            const row = document.createElement("article");
            row.className = "cart-item";
            if (item.image) {
                const image = document.createElement("img");
                image.alt = "";
                image.loading = "lazy";
                image.decoding = "async";
                image.src = item.image;
                row.append(image);
            }

            const info = document.createElement("div");
            info.className = "cart-item-info";
            const title = document.createElement("h2");
            title.textContent = item.pizza;
            info.append(title);

            const options = [];
            if (item.size) options.push(item.size + " size");
            if (item.dough) options.push(item.dough + " dough");
            if (item.crust) options.push(item.crust);
            if (item.extraToppings && item.extraToppings.length) options.push("Extra: " + item.extraToppings.join(", "));
            if (item.removedIngredients && item.removedIngredients.length) options.push("No: " + item.removedIngredients.join(", "));
            if (options.length) {
                const description = document.createElement("p");
                description.textContent = options.join(" · ");
                info.append(description);
            }
            row.append(info);

            const controls = document.createElement("div");
            controls.className = "cart-item-controls";
            const quantityField = document.createElement("div");
            quantityField.className = "cart-quantity-field";
            const quantityLabel = document.createElement("label");
            quantityLabel.textContent = "Quantity";
            const quantity = document.createElement("input");
            quantity.id = "cart-quantity-" + index;
            quantity.type = "number";
            quantity.min = "1";
            quantity.max = "99";
            quantity.step = "1";
            quantity.value = String(item.quantity);
            quantity.setAttribute("aria-label", "Quantity for " + item.pizza);
            quantity.dataset.cartQuantity = String(index);
            quantityLabel.htmlFor = quantity.id;
            const quantityControl = document.createElement("div");
            quantityControl.className = "cart-quantity-control";

            const decrease = document.createElement("button");
            decrease.type = "button";
            decrease.className = "cart-quantity-step";
            decrease.dataset.cartIndex = String(index);
            decrease.dataset.cartQuantityStep = "-1";
            decrease.setAttribute("aria-label", "Decrease quantity for " + item.pizza);
            decrease.disabled = item.quantity <= 1;
            decrease.textContent = "−";

            const increase = document.createElement("button");
            increase.type = "button";
            increase.className = "cart-quantity-step";
            increase.dataset.cartIndex = String(index);
            increase.dataset.cartQuantityStep = "1";
            increase.setAttribute("aria-label", "Increase quantity for " + item.pizza);
            increase.disabled = item.quantity >= 99;
            increase.textContent = "+";

            quantityControl.append(decrease, quantity, increase);
            quantityField.append(quantityLabel, quantityControl);

            const priceGroup = document.createElement("div");
            priceGroup.className = "cart-item-price";
            const priceLabel = document.createElement("span");
            priceLabel.textContent = "Line total";
            const price = document.createElement("strong");
            price.textContent = money(item.price);
            priceGroup.append(priceLabel, price);
            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "cart-remove";
            remove.dataset.cartRemove = String(index);
            remove.textContent = "Remove";
            remove.setAttribute("aria-label", "Remove " + item.pizza + " from your cart");
            controls.append(quantityField, priceGroup, remove);
            row.append(controls);
            list.append(row);
        });

        subtotalOutput.textContent = money(subtotal);
        countOutput.textContent = count + (count === 1 ? " item" : " items");

        restoreFocus(items);
    }

    list.addEventListener("change", function (event) {
        const input = event.target.closest("[data-cart-quantity]");
        if (!input) return;
        const index = Number(input.dataset.cartQuantity);
        try {
            focusAfterRender = { action: "input", index: index };
            window.PizzaCart.setQuantity(index, Number(input.value));
        } catch (error) {
            focusAfterRender = { action: "input", index: index };
            render();
            message.textContent = error.message;
            message.classList.add("cart-error");
            console.error("Could not update a cart quantity.", error);
        }
    });

    list.addEventListener("click", function (event) {
        const stepButton = event.target.closest("[data-cart-quantity-step]");
        if (stepButton) {
            const index = Number(stepButton.dataset.cartIndex);
            const step = Number(stepButton.dataset.cartQuantityStep);
            if (stepButton.disabled) return;
            try {
                const item = window.PizzaCart.getItems()[index];
                if (!item || (step !== -1 && step !== 1)) {
                    throw new Error("That quantity control is invalid.");
                }
                focusAfterRender = { action: "step", index: index, step: step };
                window.PizzaCart.setQuantity(index, item.quantity + step);
            } catch (error) {
                render();
                message.textContent = error.message || "Could not update the quantity.";
                message.classList.add("cart-error");
                console.error("Could not update a cart quantity.", error);
            }
            return;
        }

        const button = event.target.closest("[data-cart-remove]");
        if (!button) return;
        const index = Number(button.dataset.cartRemove);
        try {
            focusAfterRender = { action: "remove", index: index };
            window.PizzaCart.remove(index);
        } catch (error) {
            focusAfterRender = null;
            message.textContent = "We couldn’t remove that item. Please try again.";
            message.classList.add("cart-error");
            console.error("Could not remove a cart item.", error);
        }
    });

    window.addEventListener("pizza-cart-updated", render);
    render();
}());
