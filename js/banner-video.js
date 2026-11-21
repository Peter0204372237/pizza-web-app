const pizzaBannerVideo = document.querySelector(".food-motion-pizza");

if (pizzaBannerVideo instanceof HTMLVideoElement) {
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let isNearViewport = false;

    const syncPlayback = () => {
        if (!isNearViewport || document.hidden || prefersReducedMotion.matches) {
            pizzaBannerVideo.pause();
            return;
        }

        pizzaBannerVideo.play().catch((error) => {
            if (error.name !== "AbortError") {
                console.error("Unable to play the pizza banner video:", error);
            }
        });
    };

    if ("IntersectionObserver" in window) {
        const observer = new IntersectionObserver((entries) => {
            isNearViewport = entries.some((entry) => entry.isIntersecting);
            syncPlayback();
        }, { rootMargin: "100px" });
        observer.observe(pizzaBannerVideo);
    } else {
        isNearViewport = true;
        syncPlayback();
    }

    prefersReducedMotion.addEventListener("change", syncPlayback);
    document.addEventListener("visibilitychange", syncPlayback);
}
