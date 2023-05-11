ARG INSTALL_PYTHON_VERSION=${INSTALL_PYTHON_VERSION:-PYTHON_VERSION_NOT_SET}

# ================================= PRODUCTION =================================
FROM python:${INSTALL_PYTHON_VERSION}-slim-buster as production

# This allows to run any docker container as a lambda application
# From https://github.com/awslabs/aws-lambda-web-adapter
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.7.0 /lambda-adapter /opt/extensions/lambda-adapter

WORKDIR /app
ENV FLASK_APP="autoapp:app"

# Add non-root user for running the app
RUN addgroup --system quail \
    && adduser --system --ingroup quail quail
RUN chown quail:quail /app

# Install system-level packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      python3-dev

# Update pip
RUN pip install --upgrade pip

# Install production level requirements
COPY --chown=quail:quail requirements requirements/
RUN pip install --no-cache -r requirements/prod.txt

# Copy the application files
COPY --chown=quail:quail autoapp.py ./autoapp.py
COPY --chown=quail:quail backend ./backend
COPY --chown=quail:quail shell_scripts/prod_start.sh prod_start.sh
RUN chmod +x prod_start.sh

USER quail
ENV PATH="/home/quail/.local/bin:${PATH}"

CMD ["/app/prod_start.sh"]

# ================================= DEVELOPMENT ================================
FROM production AS development

RUN pip install --no-cache -r requirements/dev.txt

COPY --chown=quail:quail setup.cfg setup.cfg
COPY --chown=quail:quail shell_scripts/local_start.sh local_start.sh
RUN chmod +x local_start.sh
