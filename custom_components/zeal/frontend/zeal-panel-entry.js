import "./zeal-panel.js?v=18";

const ZealPanel = customElements.get("zeal-panel");

if (!ZealPanel) {
  throw new Error("ZEAL base panel did not register");
}

const prototype = ZealPanel.prototype;
const baseHeader = prototype._header;
const baseRenderAwayBanner = prototype._renderAwayBanner;
const baseRenderQuickChange = prototype._renderQuickChange;
const baseRenderSetup = prototype._renderSetup;
const baseRenderStandardUserAccess = prototype._renderStandardUserAccess;
const baseWarning = prototype._warning;
const baseBindEvents = prototype._bindEvents;

prototype._header = function () {
  return baseHeader
    .call(this)
    .replace('data-view="quick">Quick Change</button>', 'data-view="quick">Overrides</button>');
};

prototype._renderAwayBanner = function () {
  return baseRenderAwayBanner
    .call(this)
    .replace('data-view="setup">Away settings</button>', 'data-view="quick">Away settings</button>');
};

prototype._renderSetup = function () {
  const awaySettings = this._renderAwaySettings();
  return baseRenderSetup.call(this).replace(awaySettings, "");
};

prototype._warning = function () {
  return this._view === "setup" ? baseWarning.call(this) : "";
};

prototype._renderQuickChange = function () {
  if (this._quickLoading) return baseRenderQuickChange.call(this);

  let content = baseRenderQuickChange.call(this);
  const description = this._isAdmin()
    ? "Temporary room changes and Away Mode without editing weekly schedules."
    : "Temporary room changes without editing weekly schedules.";

  content = content
    .replace(
      "<h2>Quick Change</h2><p>Apply temporary changes without editing weekly schedules.</p>",
      `<h2>Overrides</h2><p>${description}</p>`
    )
    .replace(
      "<h2>Quick Change</h2><p>Temporary changes only. Saved weekly schedules are never edited.</p>",
      `<h2>Overrides</h2><p>${description}</p>`
    );

  if (this._quickRooms().length) {
    const firstSectionEnd = content.indexOf("</section>");
    if (firstSectionEnd !== -1) {
      const insertionPoint = firstSectionEnd + "</section>".length;
      const quickIntro = `
      <section class="setup-help">
        <strong>Quick Change</strong>
        <p>Apply temporary room temperature holds. Saved weekly schedules are never edited.</p>
      </section>`;
      content = `${content.slice(0, insertionPoint)}${quickIntro}${content.slice(insertionPoint)}`;
    }
  }

  return `${content}${this._isAdmin() ? this._renderAwaySettings() : ""}`;
};

prototype._renderStandardUserAccess = function () {
  return baseRenderStandardUserAccess
    .call(this)
    .replace(
      "Allow standard users to use Quick Change",
      "Allow standard users to use Overrides"
    )
    .replace(
      "They can apply and clear temporary room temperature changes.",
      "They can use Quick Change to apply and clear temporary room temperature changes. Away Mode remains administrator-only."
    )
    .replace(
      "Setup, Away configuration, downloads, audit and instance management remain administrator-only.",
      "Setup, Away Mode configuration, downloads, audit and instance management remain administrator-only."
    );
};

prototype._bindEvents = function () {
  this.shadowRoot.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener(
      "click",
      (event) => {
        const next = button.dataset.view;
        if (
          this._view === "quick" &&
          next !== "quick" &&
          this._awayDirty &&
          !window.confirm("Discard unsaved Away changes?")
        ) {
          event.preventDefault();
          event.stopImmediatePropagation();
        }
      },
      { capture: true }
    );
  });
  baseBindEvents.call(this);
};
