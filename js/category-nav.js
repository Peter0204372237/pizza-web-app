(function () {
    "use strict";

    const marquee = document.querySelector(".category-marquee");
    const categorySet = marquee && marquee.querySelector(".category-set");
    const track = marquee && marquee.querySelector(".category-track");
    const firstCard = categorySet && categorySet.querySelector(".category-card");
    const buttons = document.querySelectorAll("[data-scroll-direction]");

    if (!marquee || !categorySet || !track || !firstCard || buttons.length !== 2) {
        throw new Error("The category navigation controls are missing required elements.");
    }

    let resumeTimer;
    let moveFrame;

    function scrollCategories(direction) {
        const gap = parseFloat(window.getComputedStyle(categorySet).columnGap) || 0;
        const step = firstCard.getBoundingClientRect().width + gap;

        marquee.classList.add("is-manually-scrolling");
        window.clearTimeout(resumeTimer);
        window.cancelAnimationFrame(moveFrame);

        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            marquee.scrollBy({ left: direction * step, behavior: "auto" });
            resumeTimer = window.setTimeout(function () {
                marquee.classList.remove("is-manually-scrolling");
            }, 700);
            return;
        }

        const animation = track.getAnimations()[0];
        if (!animation) {
            throw new Error("The category marquee animation is unavailable.");
        }

        const cycleWidth = categorySet.getBoundingClientRect().width;
        const duration = Number(animation.effect.getTiming().duration);
        const currentTime = Number(animation.currentTime);
        if (!Number.isFinite(duration) || duration <= 0 || !Number.isFinite(currentTime) || cycleWidth <= 0) {
            throw new Error("The category marquee animation cannot be advanced.");
        }

        const cycleTime = duration * step / cycleWidth;
        const moveDuration = 450;
        const startTime = ((currentTime % duration) + duration) % duration;
        const startedAt = window.performance.now();

        function advanceAnimation(now) {
            const progress = Math.min((now - startedAt) / moveDuration, 1);
            const easedProgress = 1 - Math.pow(1 - progress, 3);
            const nextTime = startTime + direction * cycleTime * easedProgress;
            animation.currentTime = ((nextTime % duration) + duration) % duration;

            if (progress < 1) {
                moveFrame = window.requestAnimationFrame(advanceAnimation);
                return;
            }

            moveFrame = null;
            resumeTimer = window.setTimeout(function () {
                marquee.classList.remove("is-manually-scrolling");
            }, 300);
        }

        moveFrame = window.requestAnimationFrame(advanceAnimation);
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
