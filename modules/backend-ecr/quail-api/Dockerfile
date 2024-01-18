ARG INSTALL_PYTHON_VERSION=${INSTALL_PYTHON_VERSION:-PYTHON_VERSION_NOT_SET}

# ================================= PRODUCTION =================================
FROM python:${INSTALL_PYTHON_VERSION}-slim-buster as production

# This allows to run any docker container as a lambda application
# From https://github.com/awslabs/aws-lambda-web-adapter
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.7.1 /lambda-adapter /opt/extensions/lambda-adapter

WORKDIR /app

# Add non-root user for running the app
RUN addgroup --system quail \
    && adduser --system --ingroup quail quail
RUN chown quail:quail /app

# set optional environment variables for proxy
ARG http_proxy=""
ARG https_proxy=""
ARG no_proxy=""

# Install system-level packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      python3-dev

# Update pip
ARG PIP_INDEX_URL="https://pypi.python.org/simple"
RUN pip install --upgrade pip

# Install production level requirements
COPY --chown=quail:quail requirements requirements/
RUN pip install --no-cache -r requirements/prod.txt

# Copy the application files
COPY --chown=quail:quail public_app.py ./public_app.py
COPY --chown=quail:quail private_app.py ./private_app.py
COPY --chown=quail:quail backend ./backend
COPY --chown=quail:quail templates ./templates
COPY --chown=quail:quail shell_scripts/prod_start_public.sh prod_start_public.sh
COPY --chown=quail:quail shell_scripts/prod_start_private.sh prod_start_private.sh
RUN chmod +x prod_start_private.sh prod_start_public.sh

USER quail
ENV PATH="/home/quail/.local/bin:${PATH}"

# ================================= PUBLIC API ================================
FROM production AS production_public_api

CMD ["/app/prod_start_public.sh"]

# ================================= PUBLIC API ================================
FROM production AS production_private_api

CMD ["/app/prod_start_private.sh"]

# ======================== DEVELOPMENT PUBLIC API =============================
FROM production AS development_public_api

ENV FLASK_APP="public_app:app"

RUN pip install --no-cache -r requirements/dev.txt

COPY --chown=quail:quail setup.cfg setup.cfg
COPY --chown=quail:quail shell_scripts/local_start_public.sh local_start_public.sh
RUN chmod +x local_start_public.sh

CMD ["/app/local_start_public.sh"]

# ======================== DEVELOPMENT PUBLIC API =============================
FROM production AS development_private_api

ENV FLASK_APP="private_app:app"

RUN pip install --no-cache -r requirements/dev.txt

COPY --chown=quail:quail setup.cfg setup.cfg
COPY --chown=quail:quail shell_scripts/local_start_private.sh local_start_private.sh
RUN chmod +x local_start_private.sh

CMD ["/app/local_start_private.sh"]
