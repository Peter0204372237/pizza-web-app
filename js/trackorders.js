(function () {
    "use strict";

    const form = document.getElementById("track-form");
    const message = document.getElementById("track-message");
    const result = document.getElementById("track-result");
    const statuses = [
        { key: "received", title: "Order received", description: "We have your order." },
        { key: "preparing", title: "Preparing", description: "Your pizza is being prepared." },
        { key: "in_oven", title: "In the oven", description: "Your pizza is baking." },
        { key: "out_for_delivery", title: "Out for delivery", description: "A rider is on the way to you." },
        { key: "delivered", title: "Delivered", description: "Enjoy your meal." }
    ];
    const refreshDelay = 15000;
    let refreshTimer;
    let activeLookup;
    let refreshFailed = false;

    function money(value) {
        return "GH₵" + Number(value).toFixed(2).replace(/\.00$/, "");
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

    function renderOrder(order) {
        document.getElementById("result-title").textContent = "Order " + order.reference;
        const statusOutput = document.getElementById("order-status");
        if (statusOutput.textContent !== order.status_label) {
            statusOutput.textContent = order.status_label;
        }
        statusOutput.className = "eta";

        const timeline = document.getElementById("order-timeline");
        timeline.replaceChildren();
        const currentIndex = statuses.findIndex(function (status) {
            return status.key === order.status;
        });
        if (order.status === "cancelled") {
            const cancelled = document.createElement("li");
            cancelled.className = "current";
            const title = document.createElement("h3");
            title.textContent = "Cancelled";
            const description = document.createElement("p");
            description.textContent = "This order has been cancelled.";
            const content = document.createElement("div");
            content.append(title, description);
            const dot = document.createElement("span");
            dot.className = "dot";
            dot.setAttribute("aria-hidden", "true");
            cancelled.append(dot, content);
            timeline.append(cancelled);
        } else {
            statuses.forEach(function (status, index) {
                const step = document.createElement("li");
                if (index < currentIndex) {
                    step.className = "done";
                } else if (index === currentIndex) {
                    step.className = "current";
                    step.setAttribute("aria-current", "step");
                }

                const dot = document.createElement("span");
                dot.className = "dot";
                dot.setAttribute("aria-hidden", "true");
                const content = document.createElement("div");
                const title = document.createElement("h3");
                title.textContent = status.title;
                const description = document.createElement("p");
                description.textContent = status.description;
                content.append(title, description);
                step.append(dot, content);
                timeline.append(step);
            });
        }

        const itemsList = document.getElementById("tracked-order-items");
        itemsList.replaceChildren();
        order.items.forEach(function (item) {
            const row = document.createElement("li");
            const name = document.createElement("span");
            name.textContent = item.quantity + " × " + item.pizza +
                (item.size ? " (" + item.size + ")" : "");
            const price = document.createElement("span");
            price.textContent = money(item.line_total);
            row.append(name, price);
            itemsList.append(row);
        });
        const subtotal = document.createElement("li");
        const subtotalLabel = document.createElement("span");
        subtotalLabel.textContent = "Subtotal";
        const subtotalAmount = document.createElement("span");
        subtotalAmount.textContent = money(Number(order.subtotal));
        subtotal.append(subtotalLabel, subtotalAmount);
        itemsList.append(subtotal);
        (order.discounts || []).forEach(function (discount) {
            const row = document.createElement("li");
            const name = document.createElement("span");
            name.textContent = discount.title;
            const amount = document.createElement("span");
            amount.textContent = "−" + money(Number(discount.amount));
            row.append(name, amount);
            itemsList.append(row);
        });
        const total = document.createElement("li");
        total.className = "total";
        const label = document.createElement("span");
        label.textContent = "Total";
        const amount = document.createElement("span");
        amount.textContent = money(order.total);
        total.append(label, amount);
        itemsList.append(total);
        result.hidden = false;
    }

    function scheduleStatusRefresh(credentials) {
        window.clearTimeout(refreshTimer);
        refreshTimer = undefined;
        if (activeLookup !== credentials ||
            credentials.status === "delivered" ||
            credentials.status === "cancelled") {
            return;
        }
        refreshTimer = window.setTimeout(function () {
            refreshOrder(credentials);
        }, refreshDelay);
    }

    async function refreshOrder(credentials) {
        try {
            const response = await fetch("/api/orders/lookup/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken()
                },
                body: JSON.stringify({
                    order: credentials.order,
                    phone: credentials.phone
                })
            });
            const data = await response.json();
            if (activeLookup !== credentials) {
                return;
            }
            if (!response.ok) {
                throw new Error(data.error || "We couldn’t refresh your order status.");
            }

            renderOrder(data);
            credentials.status = data.status;
            if (refreshFailed) {
                message.textContent = "Order status updated.";
                refreshFailed = false;
            }
            scheduleStatusRefresh(credentials);
        } catch (error) {
            if (activeLookup !== credentials) {
                return;
            }
            message.textContent = "Could not refresh the order status. We’ll try again in 15 seconds.";
            refreshFailed = true;
            console.error("Could not refresh order status.", error);
            scheduleStatusRefresh(credentials);
        }
    }

    form.addEventListener("submit", async function (event) {
        event.preventDefault();
        if (!form.reportValidity()) {
            return;
        }

        window.clearTimeout(refreshTimer);
        refreshTimer = undefined;
        const button = form.querySelector('button[type="submit"]');
        const credentials = {
            order: document.getElementById("order-id").value.trim(),
            phone: document.getElementById("track-phone").value.trim(),
            status: null
        };
        activeLookup = credentials;
        refreshFailed = false;
        button.disabled = true;
        result.hidden = true;
        message.textContent = "Looking up your order…";
        try {
            const response = await fetch("/api/orders/lookup/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken()
                },
                body: JSON.stringify({
                    order: credentials.order,
                    phone: credentials.phone
                })
            });
            const data = await response.json();
            if (activeLookup !== credentials) {
                return;
            }
            if (!response.ok) {
                throw new Error(data.error || "We couldn’t find that order.");
            }
            credentials.status = data.status;
            renderOrder(data);
            message.textContent = "Order found. Status refreshes every 15 seconds.";
            scheduleStatusRefresh(credentials);
        } catch (error) {
            if (activeLookup !== credentials) {
                return;
            }
            message.textContent = error.message || "We couldn’t reach the tracking service. Please try again.";
            console.error("Could not track order.", error);
        } finally {
            if (activeLookup === credentials) {
                button.disabled = false;
            }
        }
    });
}());
