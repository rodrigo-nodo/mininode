# Mininode — Política de visibilidad y licencias de código

**Decisión de producto:** 03-11-2026  
**Estado:** Modelo híbrido aprobado; implementación operativa no iniciada  
**Repositorio actual:** `rodrigo-nodo/mininode` (público, licencia MIT vigente)

## Objetivo

Reservar el desarrollo comercial futuro de Mininode SpA para un ámbito **privado y propietario**, conservando una presencia pública deliberada y útil para mostrar capacidades, documentación y componentes seleccionados.

## Política aprobada

| Ámbito | Tratamiento objetivo | Observación |
|---|---|---|
| Privacy Web, Privacy Data, Capture y demás productos comerciales | Repositorio privado, con términos y titularidad determinados explícitamente | Incluye reglas de diagnóstico, scoring, Access, Billing y orquestación; no implica borrar historial ni revocar licencias anteriores |
| Portafolio, casos y documentación para clientes/partners | Público, material seleccionado | No publicar datos de clientes, claves, secretos ni lógica comercial sensible |
| Utilidades o componentes liberados intencionalmente | Repositorio público independiente, con MIT o Apache-2.0 aprobada caso a caso | Delimitar archivos, dependencias, autoría y contribuciones antes de publicar |
| Colaboraciones o demos | Según contrato y objetivo | No conceder acceso al producto interno por defecto |

**MIT actual:** el `LICENSE` existente autoriza, bajo condiciones, uso, modificación, distribución y sublicenciamiento, incluso comercial. Esa autorización no se cancela unilateralmente para copias ya obtenidas. La migración a privado afecta acceso futuro al repositorio, **no** disponibilidad ni derechos asociados a copias y forks previos.

**Futuros módulos propietarios:** no declararlos automáticamente «relicenciados» solo por moverlos a privado o borrar un archivo MIT. Mantener inventario de procedencia, autores, cesiones y componentes de terceros; decidir condiciones de nuevas contribuciones y versiones con revisión jurídica puntual. No establecer nuevas licencias comerciales ni transferir derechos sin verificar titularidad, incluida la relación entre el aviso `Copyright (c) 2025 Rodrigo` y Mininode SpA.

## Alternativas de licenciamiento

- **MIT:** simple y permisiva; apropiada para ejemplos independientes que deliberadamente permitan reutilización comercial.
- **Apache-2.0:** opción pública permisiva con términos explícitos adicionales relativos a patentes; evaluar si el componente o su ecosistema lo requiere.
- **AGPLv3:** incorpora obligaciones de ofrecer código fuente en determinados usos como servicio; no se adopta como licencia general de Mininode.
- **Propietaria:** objetivo del desarrollo comercial privado futuro, sujeto a titularidad y límites de licencias previas.
- **Dual licensing:** no se adopta ahora; reconsiderar únicamente si existe modelo comercial que lo justifique.

## Plan de transición — sin ejecutar todavía

1. **Inventario jurídico/técnico:** revisar `LICENSE`, contribuciones, archivos compartidos, historial, forks, dependencias y licencias de terceros; identificar componentes propios que se puedan separar.
2. **Diseño de repositorios:** determinar repositorio privado de producto y repositorio(s) públicos de portafolio/componentes. No mover todo el monorepo ni su historial sin estudiar efectos sobre MIT.
3. **Continuidad operativa:** inventariar GitHub Actions, permisos de GitHub App, Cloudflare Pages/Branch Previews, Render, claves/secretos y accesos de colaboradores. Probar un despliegue de rama desde repositorio privado autorizado, rollback y costo esperado antes del corte.
4. **Política de nuevas contribuciones:** documentar avisos, acuerdos con colaboradores y proceso para autorizar futuras liberaciones públicas. Determinar si corresponde titularidad o licencia a favor de Mininode SpA, con asesoría jurídica.
5. **Autorización del Product Owner:** aprobar explícitamente el plan de cambio de visibilidad/migración y fecha de corte después de comprobar seguridad y continuidad. **No ejecutar** movimientos, cambios de visibilidad, eliminación de licencias ni transferencias solo por aprobar esta política.

## Condiciones de cierre de MIN-02

- Lista verificada de lo público y privado, licencias/autoría y componentes compartidos.
- Flujo CI y despliegues equivalentes con credenciales configuradas en repositorio correcto; preview y PROD sin interrupción.
- Accesos a código/infra limitados y revisión de exposición histórica/secretos.
- Alcance y verificación de la transición aprobados; contrato y avisos legales coherentes.
- Ningún merge, cambio de visibilidad ni operación de infraestructura sin autorización explícita.

**Relación con Privacy Web:** el cambio de visibilidad **no bloquea por sí mismo** el QA funcional del piloto gratuito; sí debe planificarse antes de escalar partners o publicar más lógica comercial estratégica.
