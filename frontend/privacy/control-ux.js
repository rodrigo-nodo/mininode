// Customer-facing text only. PRV identifiers, criteria, results and scoring are defined by the backend catalog.
// One versioned catalog is shared by the public diagnosis, authenticated Plan and demo.
(() => {
  const entries = Object.freeze({
    'PRV-001': Object.freeze({ name: "Política de privacidad visible", description: "Buscamos un enlace o referencia visible a una política de privacidad en las páginas revisadas." }),
    'PRV-002': Object.freeze({ name: "Acceso a la política de privacidad", description: "Comprobamos si el enlace permite abrir contenido disponible y relacionado con privacidad." }),
    'PRV-003': Object.freeze({ name: "Política de privacidad claramente asociada a la empresa", description: "Revisamos si la política encontrada puede relacionarse claramente con la empresa o entidad responsable del sitio." }),
    'PRV-004': Object.freeze({ name: "Fecha o versión de la política", description: "Buscamos una fecha relevante o un identificador de versión visible en la política." }),
    'PRV-005': Object.freeze({ name: "Identificación del responsable", description: "Revisamos si la política identifica claramente a la organización o persona responsable." }),
    'PRV-006': Object.freeze({ name: "Contacto para temas de privacidad y derechos", description: "Buscamos un canal de contacto identificado para consultas o solicitudes relacionadas con los datos personales." }),
    'PRV-007': Object.freeze({ name: "Tipos de datos personales informados", description: "Revisamos si la política menciona tipos concretos de datos personales, como nombre, correo o teléfono." }),
    'PRV-008': Object.freeze({ name: "Para qué se utilizan los datos personales", description: "Comprobamos si la política explica finalidades concretas del tratamiento de datos." }),
    'PRV-009': Object.freeze({ name: "Fundamento declarado para tratar datos", description: "Buscamos si la política identifica el fundamento o autorización que declara para tratar datos personales." }),
    'PRV-010': Object.freeze({ name: "Si se comparten datos con terceros", description: "Revisamos si la política informa sobre destinatarios de los datos o declara que no se comunican a terceros." }),
    'PRV-011': Object.freeze({ name: "Derechos de las personas sobre sus datos", description: "Buscamos información sobre derechos concretos que las personas pueden ejercer respecto de sus datos." }),
    'PRV-012': Object.freeze({ name: "Cuánto tiempo se conservan los datos", description: "Revisamos si la política informa plazos o criterios que determinan cuánto tiempo se conservan los datos." }),
    'PRV-013': Object.freeze({ name: "Posibilidad de reclamar ante la autoridad", description: "Buscamos información sobre la posibilidad de presentar reclamaciones ante la autoridad de protección de datos." }),
    'PRV-014': Object.freeze({ name: "Retiro del consentimiento (si corresponde)", description: "Si la política declara tratamientos basados en consentimiento, revisamos si informa sobre la posibilidad de retirarlo." }),
    'PRV-101': Object.freeze({ name: "Formularios que solicitan datos personales", description: "Identificamos formularios públicos que solicitan información potencialmente personal, como nombre, correo o teléfono." }),
    'PRV-102': Object.freeze({ name: "HTTPS en el formulario y su destino", description: "Revisamos si la página del formulario y la dirección declarada para recibir sus datos utilizan HTTPS." }),
    'PRV-103': Object.freeze({ name: "Finalidad del formulario", description: "Buscamos información cercana al formulario que permita entender para qué se solicitan los datos." }),
    'PRV-104': Object.freeze({ name: "Información de privacidad en formularios", description: "Revisamos si existe información de privacidad junto al formulario y registramos las señales visibles de consentimiento o aceptación." }),
    'PRV-201': Object.freeze({ name: "Cookies observadas", description: "Registramos cookies identificadas mediante encabezados HTTP en las respuestas inspeccionadas." }),
    'PRV-301': Object.freeze({ name: "Canal de contacto visible", description: "Buscamos un correo, teléfono, formulario u otra vía pública de contacto en las páginas revisadas." }),
    'PRV-501': Object.freeze({ name: "Conexión HTTPS del sitio", description: "Comprobamos HTTPS, la validez del certificado y posibles recursos inseguros en las páginas inspeccionadas." }),
  });
  window.MininodePrivacyControlUX = Object.freeze({
    entries,
    name: (code, fallback) => entries[code]?.name ?? fallback,
    description: (code) => entries[code]?.description ?? null,
  });
})();
