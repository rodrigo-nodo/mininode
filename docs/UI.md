# Fundamentos UX/UI de Mininode

Esta guía es normativa para toda interfaz nueva o modificada. Los valores implementables viven en `frontend/assets/css/tokens.css`; este documento define cómo usarlos.

## Principios

Mininode debe sentirse minimalista, moderno, simple, tranquilo, confiable y útil antes que decorativo.

> Menos elementos, menos ruido y jerarquía clara. El producto y la acción principal deben ser protagonistas.

Evitar titulares excesivamente grandes, gradientes llamativos, exceso de cards o sombras, colores decorativos innecesarios y la estética genérica de startup/IA violeta o neón. El contenido, el espacio y una jerarquía contenida deben resolver la composición antes de añadir decoración.

## Paleta

| Rol | Valor |
| --- | --- |
| Primary | `#176B78` |
| Primary hover/dark | `#125966` |
| Primary soft | `#E8F4F5` |
| Background | `#FFFFFF` |
| Text | `#0D0F14` |
| Muted | `#626570` |
| Border | `#E5E9F2` |

El petróleo es el acento y la señal de marca; no debe dominar grandes superficies. Verde, amarillo y rojo se reservan principalmente para estados semánticos reales. No redefinir estos colores en una página: usar los tokens globales. Los temas oscuros pueden definir superficies y contrastes propios, pero deben conservar la identidad del acento.

## Tipografía

La familia de interfaz es `Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`.

La escala debe ser contenida: texto pequeño de 13–14 px, base de 16 px, destacado de 18 px, H3 de 20–24 px, H2 de 28–36 px y H1 de 36–48 px en desktop. En móvil, evitar H1 mayores de aproximadamente 36 px salvo excepción justificada. Los títulos deben sentirse más pequeños y maduros que los de una landing SaaS tradicional.

Learn puede mantener serif en el cuerpo de lectura, reutilizando los tokens globales de color, jerarquía y espaciado.

## Espaciado, bordes y composición

Usar la escala corta de espacios y radios de `tokens.css`. Preferir bordes sutiles a sombras; reservar el radio grande para contenedores que realmente necesiten agrupación. No crear un token local si uno global expresa el mismo rol.

## Componentes y accesibilidad

- `frontend/partials/header-nav.html` y `frontend/partials/footer.html` son las únicas fuentes del header y footer; las páginas deben incluirlos mediante el mecanismo común existente.
- Reutilizar botones, inputs, formularios, badges, cards básicas y estados de `frontend/assets/css/components.css` antes de crear variantes.
- Todo control interactivo debe tener nombre accesible, contraste suficiente y un estado `:focus-visible` claro.
- Conservar navegación por teclado, responsive, temas existentes y estados semánticos.
- Evitar una versión específica de página cuando el componente global puede resolver el caso.

## Fotografía

La dirección visual futura debe comunicar calma, seguridad y confianza: luz natural, composición limpia, tonos neutros, gris-azulados o naturales, espacios abiertos y arquitectura, agua, paisaje o detalles sobrios. La fotografía debe sentirse premium, no ostentosa.

La calma de interfaces fintech modernas como Mercury es una referencia conceptual; no se deben copiar imágenes, composiciones ni identidades de terceros.
