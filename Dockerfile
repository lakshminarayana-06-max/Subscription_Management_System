FROM odoo:17.0

USER root

# Install python dependencies for advanced reporting & Excel
RUN pip3 install --no-cache-dir openpyxl pandas

USER odoo
