// On "index.html"
const getStartedBtn = document.getElementById("get-started");
if (getStartedBtn) {
    getStartedBtn.addEventListener("click", function () {
        window.location.href = "getting-started.html";
    });
}

// On "getting-started.html"
const homeBtn = document.getElementById("home");
if (homeBtn) {
    homeBtn.addEventListener("click", function () {
        window.location.href = "index.html";
    });
}
