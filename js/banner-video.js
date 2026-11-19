const pizzaBannerVideo = document.querySelector(".food-motion-pizza");

if (pizzaBannerVideo instanceof HTMLVideoElement) {
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    const syncPlayback = () => {
        if (prefersReducedMotion.matches) {
            pizzaBannerVideo.pause();
            return;
        }

        pizzaBannerVideo.play().catch((error) => {
            console.error("Unable to play the pizza banner video:", error);
        });
    };

    syncPlayback();
    prefersReducedMotion.addEventListener("change", syncPlayback);
}
