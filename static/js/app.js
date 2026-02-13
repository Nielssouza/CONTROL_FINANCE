(() => {
    const backdrop = document.getElementById("modal-backdrop");
    const modalContent = document.getElementById("modal-content");
    const currencyFormatter = new Intl.NumberFormat("pt-BR", {
        style: "currency",
        currency: "BRL",
    });

    const VIEW_MODE_KEY = "control_view_mode";
    const VIEW_MODE_MOBILE = "mobile";
    const VIEW_MODE_BROWSER = "browser";

    const parseAmountToCents = (value) => {
        const raw = (value || "").toString();
        const digitsOnly = raw.replace(/\D/g, "");

        if (!digitsOnly) {
            return null;
        }

        const cents = Number.parseInt(digitsOnly, 10);
        return Number.isFinite(cents) ? Math.max(0, cents) : null;
    };

    const applyCurrencyMask = (input, cents) => {
        if (!Number.isFinite(cents)) {
            input.value = "";
            input.dataset.rawValue = "";
            return;
        }

        const safeCents = Math.max(0, cents);
        const rawValue = (safeCents / 100).toFixed(2);
        input.dataset.rawValue = rawValue;
        input.value = currencyFormatter.format(safeCents / 100);
    };

    const initCurrencyMasks = (root = document) => {
        const inputs = root.querySelectorAll('input[name="amount"], input[name="target_amount"]');

        inputs.forEach((input) => {
            if (input.dataset.currencyReady === "1") {
                return;
            }

            input.dataset.currencyReady = "1";
            input.inputMode = "numeric";
            input.autocomplete = "off";

            const initialCents = parseAmountToCents(input.value);
            if (initialCents !== null) {
                applyCurrencyMask(input, initialCents);
            } else {
                input.dataset.rawValue = "";
            }

            input.addEventListener("input", () => {
                const cents = parseAmountToCents(input.value);
                if (cents === null) {
                    input.value = "";
                    input.dataset.rawValue = "";
                    return;
                }
                applyCurrencyMask(input, cents);
            });

            input.addEventListener("blur", () => {
                if (!input.dataset.rawValue) {
                    input.value = "";
                }
            });
        });
    };

    const closeActionCards = (exceptCard = null) => {
        document.querySelectorAll("[data-press-actions].app-actions-open").forEach((card) => {
            if (card !== exceptCard) {
                card.classList.remove("app-actions-open");
            }
        });
    };

    let actionOutsideBound = false;

    const initPressActions = (root = document) => {
        const cards = root.querySelectorAll("[data-press-actions]");
        if (!cards.length) {
            return;
        }

        if (!actionOutsideBound) {
            actionOutsideBound = true;
            document.addEventListener("pointerdown", (event) => {
                if (!event.target.closest("[data-press-actions]")) {
                    closeActionCards();
                    closeTransactionActionMenus();
                }
            });
        }

        cards.forEach((card) => {
            if (card.dataset.pressReady === "1") {
                return;
            }

            card.dataset.pressReady = "1";
            let timerId = null;
            let longPressTriggered = false;

            const startPress = (event) => {
                const isCoarse = window.matchMedia && window.matchMedia("(pointer: coarse)").matches;
                if (!isCoarse) {
                    return;
                }

                if (event.target.closest("a,button,input,select,textarea,label")) {
                    return;
                }

                longPressTriggered = false;
                timerId = window.setTimeout(() => {
                    longPressTriggered = true;
                    const shouldOpen = !card.classList.contains("app-actions-open");
                    closeActionCards(card);
                    card.classList.toggle("app-actions-open", shouldOpen);
                }, 420);
            };

            const cancelPress = () => {
                if (timerId) {
                    window.clearTimeout(timerId);
                    timerId = null;
                }
            };

            card.addEventListener("pointerdown", startPress);
            card.addEventListener("pointerup", cancelPress);
            card.addEventListener("pointercancel", cancelPress);
            card.addEventListener("pointerleave", cancelPress);

            card.addEventListener("click", (event) => {
                if (longPressTriggered) {
                    event.preventDefault();
                    event.stopPropagation();
                    longPressTriggered = false;
                }
            });
        });
    };

    const getStoredViewMode = () => {
        try {
            const stored = window.localStorage.getItem(VIEW_MODE_KEY);
            return stored === VIEW_MODE_BROWSER ? VIEW_MODE_BROWSER : VIEW_MODE_MOBILE;
        } catch {
            return VIEW_MODE_MOBILE;
        }
    };

    const persistViewMode = (mode) => {
        try {
            window.localStorage.setItem(VIEW_MODE_KEY, mode);
        } catch {}
    };

    const applyViewMode = (mode) => {
        const resolvedMode = mode === VIEW_MODE_BROWSER ? VIEW_MODE_BROWSER : VIEW_MODE_MOBILE;
        document.documentElement.classList.toggle("view-browser", resolvedMode === VIEW_MODE_BROWSER);
        document.documentElement.classList.toggle("view-mobile", resolvedMode !== VIEW_MODE_BROWSER);

        const nextLabel = resolvedMode === VIEW_MODE_BROWSER ? "Modo celular" : "Modo navegador";
        document.querySelectorAll("[data-view-mode-toggle]").forEach((toggleButton) => {
            if (!(toggleButton instanceof HTMLElement)) {
                return;
            }
            toggleButton.textContent = nextLabel;
            toggleButton.setAttribute("aria-label", nextLabel);
            toggleButton.dataset.viewModeCurrent = resolvedMode;
        });
    };

    const toggleViewMode = () => {
        const currentMode = getStoredViewMode();
        const nextMode = currentMode === VIEW_MODE_BROWSER ? VIEW_MODE_MOBILE : VIEW_MODE_BROWSER;
        persistViewMode(nextMode);
        applyViewMode(nextMode);
    };

    const initViewModeToggles = (root = document) => {
        const toggles = root.querySelectorAll("[data-view-mode-toggle]");
        if (!toggles.length) {
            return;
        }

        toggles.forEach((toggleButton) => {
            if (!(toggleButton instanceof HTMLElement) || toggleButton.dataset.viewModeReady === "1") {
                return;
            }

            toggleButton.dataset.viewModeReady = "1";
            toggleButton.addEventListener("click", () => {
                toggleViewMode();
            });
        });

        applyViewMode(getStoredViewMode());
    };

    const closeTransactionActionMenus = (exceptMenu = null) => {
        document.querySelectorAll("details[data-txn-actions][open]").forEach((menu) => {
            if (menu !== exceptMenu) {
                menu.removeAttribute("open");
            }
        });
    };

    let txnMenuOutsideBound = false;

    const initTransactionActionMenus = (root = document) => {
        const menus = root.querySelectorAll("details[data-txn-actions]");
        if (!menus.length) {
            return;
        }

        if (!txnMenuOutsideBound) {
            txnMenuOutsideBound = true;
            document.addEventListener("pointerdown", (event) => {
                if (!event.target.closest("details[data-txn-actions]")) {
                    closeTransactionActionMenus();
                }
            });
        }

        menus.forEach((menu) => {
            if (menu.dataset.dropdownReady === "1") {
                return;
            }

            menu.dataset.dropdownReady = "1";
            menu.addEventListener("toggle", () => {
                if (menu.open) {
                    closeTransactionActionMenus(menu);
                }
            });
        });
    };

    const openModal = () => {
        if (!backdrop) {
            return;
        }

        backdrop.classList.remove("hidden");
        backdrop.classList.add("flex");
        document.body.classList.add("overflow-hidden");
    };

    const closeModal = () => {
        if (!backdrop || !modalContent) {
            return;
        }

        backdrop.classList.add("hidden");
        backdrop.classList.remove("flex");
        modalContent.innerHTML = "";
        document.body.classList.remove("overflow-hidden");
    };

    window.financeApp = { openModal, closeModal };

    if (backdrop) {
        backdrop.addEventListener("click", (event) => {
            if (event.target.id === "modal-backdrop") {
                closeModal();
            }
        });
    }

    document.body.addEventListener("htmx:afterSwap", (event) => {
        if (event.detail && event.detail.target) {
            initCurrencyMasks(event.detail.target);
            initPressActions(event.detail.target);
            initTransactionActionMenus(event.detail.target);
            initViewModeToggles(event.detail.target);
        }

        if (
            backdrop
            && modalContent
            && event.detail
            && event.detail.target
            && event.detail.target.id === "modal-content"
            && modalContent.innerHTML.trim()
        ) {
            openModal();
        }
    });

    document.addEventListener(
        "submit",
        (event) => {
            const form = event.target;
            if (!(form instanceof HTMLFormElement)) {
                return;
            }

            const currencyInputs = form.querySelectorAll('input[data-currency-ready="1"]');
            if (!currencyInputs.length) {
                return;
            }

            currencyInputs.forEach((currencyInput) => {
                currencyInput.value = currencyInput.dataset.rawValue || currencyInput.value;
            });
        },
        true
    );

    document.body.addEventListener("closeModal", closeModal);

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeModal();
            closeActionCards();
            closeTransactionActionMenus();
        }
    });

    initCurrencyMasks(document);
    initPressActions(document);
    initTransactionActionMenus(document);
    initViewModeToggles(document);
    applyViewMode(getStoredViewMode());
})();
