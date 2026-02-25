/**
 * Isha Framework — Landing Page Interactions
 */

(function () {
    "use strict";

    // ── Theme toggle ───────────────────────────────────
    const themeToggle = document.getElementById("theme-toggle");
    const root = document.documentElement;

    function setTheme(theme) {
        root.setAttribute("data-theme", theme);
        localStorage.setItem("isha-theme", theme);
    }

    // Load saved preference or respect system setting
    const saved = localStorage.getItem("isha-theme");
    if (saved) {
        setTheme(saved);
    } else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches) {
        setTheme("light");
    }

    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            const current = root.getAttribute("data-theme");
            setTheme(current === "light" ? "dark" : "light");
        });
    }

    // ── Navbar scroll effect ───────────────────────────
    const navbar = document.getElementById("navbar");
    function updateNav() {
        if (window.scrollY > 40) {
            navbar.classList.add("scrolled");
        } else {
            navbar.classList.remove("scrolled");
        }
    }
    window.addEventListener("scroll", updateNav, { passive: true });
    updateNav();

    // ── Mobile menu toggle ─────────────────────────────
    const toggle = document.getElementById("nav-toggle");
    const navLinks = document.getElementById("nav-links");

    if (toggle && navLinks) {
        toggle.addEventListener("click", () => {
            navLinks.classList.toggle("open");
            toggle.classList.toggle("active");
        });

        // Close menu on link click
        navLinks.querySelectorAll("a").forEach((link) => {
            link.addEventListener("click", () => {
                navLinks.classList.remove("open");
                toggle.classList.remove("active");
            });
        });
    }

    // ── Code tabs ──────────────────────────────────────
    const tabs = document.querySelectorAll(".code-tab");
    const panels = document.querySelectorAll(".code-panel");

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            const target = tab.dataset.tab;

            tabs.forEach((t) => t.classList.remove("active"));
            panels.forEach((p) => p.classList.remove("active"));

            tab.classList.add("active");
            const panel = document.getElementById("panel-" + target);
            if (panel) panel.classList.add("active");
        });
    });

    // ── Scroll-reveal animation ────────────────────────
    const revealElements = document.querySelectorAll(
        ".feature-card, .step-card, .eco-card, .sare-card, .sare-flow-item, .sare-compare"
    );

    if ("IntersectionObserver" in window) {
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry, idx) => {
                    if (entry.isIntersecting) {
                        // Stagger animation by index within current batch
                        const siblings = Array.from(
                            entry.target.parentElement.children
                        );
                        const index = siblings.indexOf(entry.target);
                        entry.target.style.transitionDelay = index * 0.07 + "s";
                        entry.target.classList.add("visible");
                        observer.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
        );

        revealElements.forEach((el) => observer.observe(el));
    } else {
        // Fallback: just show everything
        revealElements.forEach((el) => el.classList.add("visible"));
    }

    // ── Smooth scroll for anchor links ─────────────────
    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
        anchor.addEventListener("click", function (e) {
            const targetId = this.getAttribute("href");
            if (targetId === "#") return;
            const target = document.querySelector(targetId);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: "smooth" });
            }
        });
    });
})();
