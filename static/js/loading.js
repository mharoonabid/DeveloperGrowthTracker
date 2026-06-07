(function () {
    const overlay = document.getElementById("loading-overlay");
    if (!overlay) {
        return;
    }

    const messageEl = overlay.querySelector(".loading-message");
    const steps = [
        "Fetching GitHub profile…",
        "Loading repositories…",
        "Analyzing languages in parallel…",
        "Building contribution graph…",
        "Almost done…",
    ];
    let stepIndex = 0;
    let stepTimer = null;

    function cycleMessage() {
        if (!messageEl) {
            return;
        }
        messageEl.textContent = steps[stepIndex % steps.length];
        stepIndex += 1;
    }

    function showLoading() {
        overlay.hidden = false;
        document.body.classList.add("is-loading");
        cycleMessage();
        stepTimer = window.setInterval(cycleMessage, 2200);
    }

    document.querySelectorAll("form[data-loading]").forEach((form) => {
        form.addEventListener("submit", () => {
            const button = form.querySelector('button[type="submit"]');
            if (button) {
                button.disabled = true;
            }
            showLoading();
        });
    });
})();
