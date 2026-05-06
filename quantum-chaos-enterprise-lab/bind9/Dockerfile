FROM internetsystemsconsortium/bind9:9.18

COPY named.conf /etc/bind/named.conf
COPY named.conf.options /etc/bind/named.conf.options
COPY zones.conf /etc/bind/zones.conf
COPY zones/ /etc/bind/zones/

# Ensure bind user can read zone files
RUN chown -R bind:bind /etc/bind/zones/
