/*
 * ComplaintAgent AI — lógica de la interfaz web (JavaScript vanilla).
 *
 * La interfaz es solo un cliente de la API existente:
 *   POST /agent/complaint  (ruta RELATIVA, funciona en localhost y en EC2)
 * No contiene credenciales ni lógica de clasificación; el backend sigue
 * siendo la fuente de verdad (incluida la validación con Pydantic).
 */
(function () {
  "use strict";

  const API_URL = "/agent/complaint";

  // Etiquetas legibles para los valores que devuelve la API (docs/api.md).
  const LABELS = {
    category: {
      entrega: "Entrega",
      facturacion: "Facturación",
      producto: "Producto",
      servicio: "Servicio",
      otro: "Otro",
    },
    severity: { baja: "Baja", media: "Media", alta: "Alta", critica: "Crítica" },
    sentiment: { positivo: "Positivo", neutral: "Neutral", negativo: "Negativo" },
    priority: { baja: "Baja", media: "Media", urgente: "Urgente" },
  };

  // Color de cada valor: verde = normal, naranja = advertencia, rojo = alto.
  const TONES = {
    severity: { baja: "ok", media: "warn", alta: "danger", critica: "danger" },
    sentiment: { positivo: "ok", neutral: "neutral", negativo: "warn" },
    priority: { baja: "ok", media: "warn", urgente: "danger" },
  };

  const FIELD_NAMES = {
    complaint_id: "ID de queja",
    customer_id: "ID del cliente",
    channel: "Canal",
    message: "Mensaje de la queja",
  };

  const REVIEW_THRESHOLD = 0.8; // Igual que CONFIDENCE_THRESHOLD en app/rules.py

  const ICONS = {
    check:
      '<svg class="icon" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/><path d="M7.5 12.5l3 3 6-6.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    info:
      '<svg class="icon" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 11v6M12 7.5v.01" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>',
    warn:
      '<svg class="icon" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M12 3l10 18H2z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M12 10v5M12 18v.01" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>',
  };

  const $ = (id) => document.getElementById(id);

  const form = $("complaint-form");
  const submitBtn = $("submit-btn");
  const submitLabel = submitBtn.querySelector(".btn__label");
  const resetBtn = $("reset-btn");

  const states = {
    empty: $("state-empty"),
    loading: $("state-loading"),
    error: $("state-error"),
    result: $("state-result"),
  };

  // ---------------------------------------------------------------- Estados

  function showState(name) {
    Object.entries(states).forEach(([key, el]) => {
      el.hidden = key !== name;
    });
  }

  function setLoading(isLoading) {
    submitBtn.disabled = isLoading;
    resetBtn.disabled = isLoading;
    submitBtn.classList.toggle("is-loading", isLoading);
    submitLabel.textContent = isLoading ? "Analizando queja..." : "Analizar queja";
    if (isLoading) showState("loading");
  }

  function showError(title, text) {
    $("error-title").textContent = title;
    $("error-text").textContent = text;
    showState("error");
    revealResult();
  }

  // En pantallas angostas (una columna) el resultado queda debajo del
  // formulario: se desplaza la vista para que el usuario lo vea.
  function revealResult() {
    if (window.matchMedia("(max-width: 899px)").matches) {
      $("result-title").scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  // -------------------------------------------------------------- Validación

  function setFieldError(name, message) {
    const input = form.elements[name];
    const field = input.closest(".field");
    $(name + "-error").textContent = message || "";
    field.classList.toggle("has-error", Boolean(message));
    input.setAttribute("aria-invalid", message ? "true" : "false");
  }

  function clearErrors() {
    Object.keys(FIELD_NAMES).forEach((name) => setFieldError(name, ""));
  }

  function readForm() {
    return {
      complaint_id: form.elements.complaint_id.value.trim(),
      customer_id: form.elements.customer_id.value.trim(),
      channel: form.elements.channel.value,
      message: form.elements.message.value.trim(),
    };
  }

  // Validación básica en el navegador. El backend (Pydantic) sigue validando.
  function validate(data) {
    let firstInvalid = null;
    Object.keys(FIELD_NAMES).forEach((name) => {
      if (!data[name]) {
        const msg = name === "channel" ? "Seleccione un canal." : "Este campo es obligatorio.";
        setFieldError(name, msg);
        firstInvalid = firstInvalid || name;
      }
    });
    if (firstInvalid) form.elements[firstInvalid].focus();
    return !firstInvalid;
  }

  // --------------------------------------------------------------- Resultado

  function label(group, value) {
    return (LABELS[group] && LABELS[group][value]) || value;
  }

  function setPill(id, group, value, toneOverride) {
    const el = $(id);
    const tone = toneOverride || (TONES[group] && TONES[group][value]) || "info";
    el.textContent = label(group, value);
    el.className = "pill tone-" + tone;
  }

  function setBanner(id, tone, icon, text) {
    const el = $(id);
    el.className = el.className.split(" ")[0] + " tone-" + tone;
    el.innerHTML = ICONS[icon];
    const span = document.createElement("span");
    span.textContent = text; // textContent: nunca se inserta HTML desde la API
    el.appendChild(span);
  }

  function renderResult(r) {
    if (r.is_complaint) {
      setBanner("r-status", "info", "check", "Es una queja");
    } else {
      setBanner("r-status", "neutral", "info", "No parece ser una queja");
    }

    setPill("r-category", "category", r.category, "info");
    setPill("r-severity", "severity", r.severity);
    setPill("r-sentiment", "sentiment", r.sentiment);
    setPill("r-priority", "priority", r.priority);

    const pct = Math.round(Math.max(0, Math.min(1, Number(r.confidence) || 0)) * 100);
    $("r-confidence-value").textContent = pct + "%";
    const fill = $("r-confidence-fill");
    fill.classList.toggle("is-low", r.confidence < REVIEW_THRESHOLD);
    $("r-confidence-bar").setAttribute("aria-valuenow", String(pct));
    fill.style.width = "0";
    requestAnimationFrame(() => {
      fill.style.width = pct + "%";
    });

    $("r-summary").textContent = r.summary;
    $("r-action").textContent = r.recommended_action;

    if (r.needs_human_review) {
      setBanner("r-review", "warn", "warn", "Revisión humana requerida");
    } else {
      setBanner("r-review", "ok", "check", "No requiere revisión humana");
    }

    $("r-id").textContent = r.complaint_id;
    showState("result");
    revealResult();
  }

  // ---------------------------------------------------------------- Envío

  async function analyze(data) {
    setLoading(true);
    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(data),
      });

      let body = null;
      try {
        body = await response.json();
      } catch (parseError) {
        console.error("Respuesta no JSON del servidor:", parseError);
      }

      if (response.ok && body) {
        renderResult(body);
        return;
      }

      console.error("Error HTTP", response.status, body);

      if (response.status === 400 && body && Array.isArray(body.details)) {
        // Errores de validación del backend: marcar los campos afectados.
        const fields = body.details
          .map((d) => d.field)
          .filter((f) => FIELD_NAMES[f]);
        fields.forEach((f) => setFieldError(f, "Revise este campo."));
        const names = fields.map((f) => FIELD_NAMES[f]).join(", ");
        showError(
          "Los datos enviados no son válidos.",
          names ? "Revise los campos: " + names + "." : "Revise la información e inténtelo nuevamente."
        );
        return;
      }

      showError(
        "No fue posible analizar la queja.",
        "Verifique que el servicio esté disponible e inténtelo nuevamente."
      );
    } catch (networkError) {
      console.error("Error de conexión con la API:", networkError);
      showError(
        "No fue posible analizar la queja.",
        "Verifique que el servicio esté disponible e inténtelo nuevamente."
      );
    } finally {
      setLoading(false);
    }
  }

  // --------------------------------------------------------------- Eventos

  form.addEventListener("submit", (event) => {
    event.preventDefault(); // sin recargar la página
    clearErrors();
    const data = readForm();
    if (!validate(data)) return;
    analyze(data);
  });

  // Quitar el error de un campo en cuanto el usuario lo corrige.
  Object.keys(FIELD_NAMES).forEach((name) => {
    const input = form.elements[name];
    const evt = input.tagName === "SELECT" ? "change" : "input";
    input.addEventListener(evt, () => {
      if (input.value.trim()) setFieldError(name, "");
    });
  });

  resetBtn.addEventListener("click", () => {
    form.reset();
    clearErrors();
    showState("empty");
    form.elements.complaint_id.focus();
  });

  showState("empty");
})();
