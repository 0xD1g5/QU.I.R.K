# Phase 80 D-80-R7 fallback image — tertiary fallback only (see adcs/README.md).
#
# Plan 80-01 ran into TWO schema-load issues:
#   1. PRIMARY (`ldapadd -Y EXTERNAL` against cn=config from the seed sidecar):
#      Insufficient access (50). cn=config writes require EXTERNAL on the
#      container's ldapi:/// socket, not the network ldap:// listener.
#   2. THIS FALLBACK (`COPY ... /opt/bitnami/openldap/etc/schema/`):
#      Bitnami's entrypoint does NOT auto-include arbitrary *.ldif dropped
#      into etc/schema/ — it only loads the well-known core/cosine/
#      inetorgperson/nis chain plus $LDAP_CUSTOM_SCHEMA_FILE/_DIR.
#
# The compose `adcs-openldap` service therefore uses Bitnami's NATIVE schema
# load path (LDAP_CUSTOM_SCHEMA_DIR=/schemas + bind-mounted adcs/schema/).
# That keeps the service definition pure `image:` (no build step required),
# which is faster + matches the rest of the lab.
#
# This Dockerfile is preserved per the plan's "ship both branches" contract
# (D-80-R7) so it remains available as a tertiary fallback if a future
# Bitnami image release breaks the LDAP_CUSTOM_SCHEMA_DIR contract. To
# activate: switch `image:` -> `build: ./adcs/` on `adcs-openldap` and drop
# the LDAP_CUSTOM_SCHEMA_DIR / LDAP_EXTRA_SCHEMAS env entries (or override
# them appropriately if you also want msuser loaded).

FROM bitnamilegacy/openldap:2.6.10-debian-12-r4
COPY schema/msPKI-schema.ldif /opt/bitnami/openldap/etc/schema/msPKI.ldif
