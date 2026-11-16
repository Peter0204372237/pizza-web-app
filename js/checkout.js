(function () {
    "use strict";

    const form = document.getElementById("checkout-form");
    const empty = document.getElementById("checkout-empty");
    const content = document.getElementById("checkout-content");
    const summary = document.getElementById("checkout-summary");
    const subtotalOutput = document.getElementById("checkout-subtotal");
    const discountOutput = document.getElementById("checkout-discounts");
    const totalOutput = document.getElementById("checkout-total-amount");
    const message = document.getElementById("checkout-message");
    const confirmation = document.getElementById("checkout-confirmation");
    const submitButton = form.querySelector('button[type="submit"]');
    let quoteRequest = 0;
    let currentItems = [];
    let quoteReady = false;

    function money(value) {
        return "GH₵" + value.toFixed(2).replace(/\.00$/, "");
    }

    function csrfToken() {
        const cookie = document.cookie.split("; ").find(function (entry) {
            return entry.startsWith("csrftoken=");
        });
        if (!cookie) {
            throw new Error("Security token missing. Refresh the page and try again.");
        }
        return decodeURIComponent(cookie.slice("csrftoken=".length));
    }

    function orderItems(items) {
        return items.map(function (item) {
            return {
                slug: item.slug,
                pizza: item.pizza,
                quantity: item.quantity,
                size: item.size,
                dough: item.dough,
                crust: item.crust,
                extraToppings: item.extraToppings || [],
                removedIngredients: item.removedIngredients || []
            };
        });
    }

    function renderSummary(quote) {
        if (quote) {
            summary.replaceChildren();
            quote.items.forEach(function (item) {
                const row = document.createElement("li");
                const title = document.createElement("span");
                title.textContent = item.quantity + " × " + item.pizza + " (" + item.size + ")";
                const price = document.createElement("strong");
                price.textContent = money(Number(item.line_total));
                row.append(title, price);
                summary.append(row);
            });
            subtotalOutput.textContent = money(Number(quote.subtotal));
            discountOutput.replaceChildren();
            quote.discounts.forEach(function (discount) {
                const row = document.createElement("li");
                const title = document.createElement("span");
                title.textContent = discount.title;
                const amount = document.createElement("strong");
                amount.textContent = "−" + money(Number(discount.amount));
                row.append(title, amount);
                discountOutput.append(row);
            });
            discountOutput.hidden = quote.discounts.length === 0;
            totalOutput.textContent = money(Number(quote.total));
            return;
        }

        try {
            currentItems = window.PizzaCart.getItems();
        } catch (error) {
            message.textContent = "We couldn’t load your cart. Please return to the cart and check your saved site data.";
            message.classList.add("cart-error");
            content.hidden = true;
            empty.hidden = true;
            console.error("Could not load checkout cart.", error);
            return;
        }

        summary.replaceChildren();
        currentItems.forEach(function (item) {
            const row = document.createElement("li");
            const title = document.createElement("span");
            title.textContent = item.quantity + " × " + item.pizza + (item.size ? " (" + item.size + ")" : "");
            const price = document.createElement("strong");
            price.textContent = money(item.price);
            row.append(title, price);
            summary.append(row);
        });

        subtotalOutput.textContent = "Calculating…";
        totalOutput.textContent = "Calculating…";
        discountOutput.hidden = true;
        empty.hidden = currentItems.length > 0;
        content.hidden = currentItems.length === 0;
        return currentItems;
    }

    async function refreshQuote(items) {
        const requestId = ++quoteRequest;
        quoteReady = false;
        submitButton.disabled = true;
        if (!items.length) {
            return;
        }
        message.textContent = "Checking current prices and offers…";
        message.classList.remove("cart-error");
        try {
            const response = await fetch("/api/orders/quote/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken()
                },
                body: JSON.stringify({ items: orderItems(items) })
            });
            const quote = await response.json();
            if (requestId !== quoteRequest) {
                return;
            }
            if (!response.ok) {
                throw new Error(quote.error || "We couldn’t calculate your order total.");
            }
            renderSummary(quote);
            quoteReady = true;
            submitButton.disabled = false;
            message.textContent = quote.discounts.length
                ? "The best eligible offer has been applied to this order."
                : "Current menu prices confirmed. No automatic offer applies to these items today.";
        } catch (error) {
            if (requestId !== quoteRequest) {
                return;
            }
            message.textContent = error.message || "We couldn’t calculate your order total.";
            message.classList.add("cart-error");
            console.error("Could not calculate checkout total.", error);
        }
    }

    form.addEventListener("submit", async function (event) {
        event.preventDefault();
        if (!form.reportValidity()) return;

        const submitButton = form.querySelector('button[type="submit"]');
        try {
            const items = window.PizzaCart.getItems();
            if (!items.length) {
                renderSummary();
                message.textContent = "Your cart is empty. Add a pizza before placing your order.";
                message.classList.add("cart-error");
                return;
            }

            if (!quoteReady) {
                throw new Error("Please wait for the current order total to finish calculating.");
            }
            submitButton.disabled = true;
            message.textContent = "Sending your order…";
            message.classList.remove("cart-error");
            const response = await fetch("/api/orders/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken()
                },
                body: JSON.stringify({
                    customer: {
                        name: document.getElementById("customer-name").value.trim(),
                        phone: document.getElementById("customer-phone").value.trim(),
                        address: document.getElementById("delivery-address").value.trim(),
                        city: document.getElementById("delivery-city").value.trim(),
                        instructions: document.getElementById("delivery-instructions").value.trim()
                    },
                    items: orderItems(items)
                })
            });
            const order = await response.json();
            if (!response.ok) {
                throw new Error(order.error || "We couldn’t place your order.");
            }

            window.PizzaCart.clear();
            content.hidden = true;
            confirmation.hidden = false;
            document.getElementById("confirmation-order-id").textContent = order.reference;
            document.getElementById("confirmation-total").textContent = money(Number(order.total));
            if (order.discounts && order.discounts.length > 0) {
                document.getElementById("confirmation-discount").textContent =
                    order.discounts.map(function (discount) {
                        return discount.title + " (−" + money(Number(discount.amount)) + ")";
                    }).join(", ");
                document.getElementById("confirmation-discount-row").hidden = false;
            }
            window.scrollTo(0, 0);
        } catch (error) {
            message.textContent = error.message || "We couldn’t reach the order service. Please try again.";
            message.classList.add("cart-error");
            console.error("Could not place order.", error);
        } finally {
            submitButton.disabled = false;
        }
    });

    const initialItems = renderSummary();
    if (initialItems) {
        refreshQuote(initialItems);
    }

    window.addEventListener("pizza-cart-updated", function () {
        const items = renderSummary();
        if (items) {
            refreshQuote(items);
        }
    });
}());
