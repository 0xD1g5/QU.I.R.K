FROM alpine:3.19
RUN apk add --no-cache net-snmp net-snmp-tools
COPY snmpd.conf /etc/snmp/snmpd.conf
EXPOSE 161/udp
CMD ["snmpd", "-f", "-Lo", "-c", "/etc/snmp/snmpd.conf"]
