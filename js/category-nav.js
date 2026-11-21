(function () {
    "use strict";

    const marquee = document.querySelector(".category-marquee");
    const categorySet = marquee && marquee.querySelector(".category-set");
    const firstCard = categorySet && categorySet.querySelector(".category-card");
    const buttons = document.querySelectorAll("[data-scroll-direction]");

    if (!marquee || !categorySet || !firstCard || buttons.length !== 2) {
        throw new Error("The category navigation controls are missing required elements.");
    }

    function scrollCategories(direction) {
        const gap = parseFloat(window.getComputedStyle(categorySet).columnGap) || 0;
        const step = firstCard.getBoundingClientRect().width + gap;
        const behavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches
            ? "auto"
            : "smooth";
        marquee.scrollBy({ left: direction * step, behavior: behavior });
    }

    buttons.forEach(function (button) {
        button.addEventListener("click", function () {
            const direction = Number(button.dataset.scrollDirection);
            if (direction !== -1 && direction !== 1) {
                throw new Error("Category navigation direction must be -1 or 1.");
            }
            scrollCategories(direction);
        });
    });
}());
