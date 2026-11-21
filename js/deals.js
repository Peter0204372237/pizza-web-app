(function () {
    "use strict";

    const message = document.getElementById("deals-message");
    const featured = document.getElementById("featured-deal");
    const featuredTemplate = document.getElementById("featured-deal-template");
    const moreDeals = document.getElementById("more-deals-section");
    const dealGrid = document.getElementById("deal-grid");
    const cardTemplate = document.getElementById("deal-card-template");

    function renderPrices(container, deal) {
        const displayedPrice = deal.promotion_price === null
            ? deal.offer_text
            : "GH₵" + Number(deal.promotion_price).toFixed(2).replace(/\.00$/, "");
        container.querySelector(".price-new").textContent = displayedPrice;
        const previousPrice = container.querySelector(".price-old");
        if (deal.previous_price !== null) {
            previousPrice.textContent = "GH₵" + Number(deal.previous_price).toFixed(2);
            previousPrice.hidden = false;
        }
    }

    function setOfferContent(container, deal, titleSelector, badgeSelector) {
        const image = container.querySelector("img");
        image.decoding = "async";
        image.src = deal.image;
        image.alt = deal.image_alt;
        container.querySelector(titleSelector).textContent = deal.title;
        container.querySelector(".deal-description").textContent = deal.description;
        container.querySelector(badgeSelector).textContent = deal.badge;
        container.querySelector(badgeSelector).hidden = !deal.badge;
        renderPrices(container, deal);
        const link = container.querySelector("a");
        link.href = deal.button_url;
        link.textContent = deal.button_text;
    }

    function renderDeals(deals) {
        if (!Array.isArray(deals) || deals.some(function (deal) {
            return !deal || typeof deal.title !== "string" ||
                typeof deal.badge !== "string" ||
                typeof deal.description !== "string" ||
                typeof deal.image !== "string" ||
                typeof deal.image_alt !== "string" ||
                typeof deal.offer_text !== "string" ||
                (deal.promotion_price !== null &&
                    (typeof deal.promotion_price !== "string" ||
                        !Number.isFinite(Number(deal.promotion_price)))) ||
                (deal.previous_price !== null &&
                    (typeof deal.previous_price !== "string" ||
                        !Number.isFinite(Number(deal.previous_price)))) ||
                typeof deal.button_text !== "string" ||
                typeof deal.button_url !== "string" ||
                typeof deal.is_featured !== "boolean";
        })) {
            throw new Error("The offers from the server are invalid.");
        }

        const featuredDeal = deals.find(function (deal) {
            return deal.is_featured;
        });
        const otherDeals = deals.filter(function (deal) {
            return deal !== featuredDeal;
        });

        if (featuredDeal) {
            featured.replaceChildren(featuredTemplate.content.cloneNode(true));
            const image = featured.querySelector(".deal-feature-img");
            image.decoding = "async";
            image.src = featuredDeal.image;
            image.alt = featuredDeal.image_alt;
            const badge = featured.querySelector(".deal-label");
            badge.textContent = featuredDeal.badge;
            badge.hidden = !featuredDeal.badge;
            featured.querySelector(".deal-feature-body h2").textContent = featuredDeal.title;
            featured.querySelector(".deal-description").textContent = featuredDeal.description;
            renderPrices(featured, featuredDeal);
            const link = featured.querySelector("a");
            link.href = featuredDeal.button_url;
            link.textContent = featuredDeal.button_text;
            featured.hidden = false;
        } else {
            featured.hidden = true;
        }

        dealGrid.replaceChildren();
        otherDeals.forEach(function (deal) {
            const card = cardTemplate.content.firstElementChild.cloneNode(true);
            setOfferContent(card, deal, "h3", ".deal-chip");
            dealGrid.append(card);
        });
        moreDeals.hidden = otherDeals.length === 0;
        message.hidden = deals.length > 0;
        if (deals.length === 0) {
            message.textContent = "There are no current offers. Please check back soon.";
        }
    }

    fetch("/api/deals/")
        .then(function (response) {
            if (!response.ok) {
                throw new Error("The offers could not be loaded from the server.");
            }
            return response.json();
        })
        .then(function (data) {
            renderDeals(data.deals);
        })
        .catch(function (error) {
            message.textContent = error.message || "We couldn’t load the current offers.";
            console.error("Could not load deals.", error);
        });
}());
