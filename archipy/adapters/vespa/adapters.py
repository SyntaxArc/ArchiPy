import logging
import ssl
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Literal, cast, override

import httpx
from vespa.application import Vespa, VespaAsync, VespaSync
from vespa.package import ApplicationPackage

from archipy.adapters.vespa.ports import (
    AsyncVespaPort,
    VespaDocumentType,
    VespaDocumentTypeType,
    VespaIdType,
    VespaPort,
    VespaResponseType,
    VespaSchemaType,
)
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import VespaConfig

logger = logging.getLogger(__name__)


class CustomVespaSync(VespaSync):
    """Custom implementation of VespaSync that supports HTTP/2 configuration.

    This class extends the standard VespaSync client to provide better control
    over HTTP protocol versions and connection management.
    """

    def __init__(
        self,
        app: Vespa,
        http_version: Literal["HTTP/2", "HTTP/1.1"] = "HTTP/2",
        timeout: int = 60,
        **kwargs: object,
    ) -> None:
        """Initialize the CustomVespaSync client.

        Args:
            app: The Vespa application instance
            http_version: HTTP version to use ("HTTP/2" or "HTTP/1.1")
            timeout: Request timeout in seconds
            **kwargs: Additional arguments passed to the httpx client
        """
        super().__init__(app=app)
        self.http_version = http_version
        self.timeout = timeout
        self.httpx_client: httpx.Client | None = None
        self.kwargs: dict[str, Any] = kwargs
        self.last_response_headers: dict[str, str] | None = None

    def _open_httpx_client(self) -> httpx.Client:
        """Open and configure the httpx client.

        Returns:
            httpx.Client: The configured httpx client
        """
        if self.httpx_client is not None:
            return self.httpx_client

        verify: bool | ssl.SSLContext = False
        if self.app.cert is not None:
            if self.app.key is not None:
                verify = httpx.create_ssl_context(cert=(self.app.cert, self.app.key))
            else:
                verify = httpx.create_ssl_context(cert=self.app.cert)

        # Set http2 and http1 flags based on the http_version
        use_http2 = self.http_version == "HTTP/2"

        self.httpx_client = httpx.Client(
            timeout=self.timeout,
            headers=self.headers,
            verify=verify,
            http2=use_http2,
            http1=not use_http2,
            **self.kwargs,
        )
        self.http_session = self.httpx_client  # type: ignore

        logger.info(f"Opened httpx client for VespaSync with configured HTTP version: {self.http_version}")
        logger.info(f"Client details: {self.httpx_client}")

        try:
            test_url = f"{self.app.end_point}/status"
            test_response = self.httpx_client.get(test_url)
            self.last_response_headers = dict(test_response.headers)
            logger.info(f"Test request made to {test_url}")
            logger.info(f"Response status: {test_response.status_code}")
            logger.info(f"Response headers: {test_response.headers}")
            if "Via" in test_response.headers:
                logger.info(f"Via header: {test_response.headers['Via']}")
            if hasattr(test_response, "http_version"):
                logger.info(f"HTTP version from response: {test_response.http_version}")
        except Exception as e:
            logger.warning(f"Failed to make test request: {e}")

        return self.httpx_client

    def get_http_version(self) -> str:
        """Return the HTTP version being used by this client.

        Returns:
            str: Detailed information about the HTTP version configuration and status
        """
        if self.httpx_client is None:
            return f"Configured to use {self.http_version}, but client is not initialized yet"

        headers_info = ""
        if self.last_response_headers:
            headers_info = f", Last response headers: {self.last_response_headers}"

        return f"Configured to use {self.http_version}{headers_info}"

    def close(self) -> None:
        """Close internal HTTP client, just like VespaSync.close()."""
        if self.httpx_client is not None:
            self.httpx_client.close()
            self.httpx_client = None
            self.http_session = None  # type: ignore


class CustomVespaAsync(VespaAsync):
    """Custom implementation of VespaAsync that supports HTTP/2 configuration.

    This class extends the standard VespaAsync client to provide better control
    over HTTP protocol versions and connection management for asynchronous operations.
    """

    def __init__(
        self,
        app: Vespa,
        http_version: Literal["HTTP/2", "HTTP/1.1"] = "HTTP/2",
        timeout: int = 60,
        **kwargs: object,
    ) -> None:
        """Initialize the CustomVespaAsync client.

        Args:
            app: The Vespa application instance
            http_version: HTTP version to use ("HTTP/2" or "HTTP/1.1")
            timeout: Request timeout in seconds
            **kwargs: Additional arguments passed to the httpx client
        """
        super().__init__(app=app)
        self.http_version = http_version
        self.timeout = timeout
        self.httpx_client = None
        self.kwargs: dict[str, Any] = kwargs
        self.last_response_headers: dict[str, str] | None = None
        self._open_httpx_client()

    def _open_httpx_client(self) -> httpx.AsyncClient:
        """Open and configure the httpx async client.

        Returns:
            httpx.AsyncClient: The configured httpx async client
        """
        if self.httpx_client is not None:
            return self.httpx_client

        verify: bool | ssl.SSLContext = False
        if self.app.cert is not None:
            if self.app.key is not None:
                verify = httpx.create_ssl_context(cert=(self.app.cert, self.app.key))
            else:
                verify = httpx.create_ssl_context(cert=self.app.cert)

        use_http2 = self.http_version == "HTTP/2"

        self.httpx_client = httpx.AsyncClient(  # type: ignore
            timeout=self.timeout,
            headers=self.headers,
            verify=verify,
            http2=use_http2,
            http1=not use_http2,
            **self.kwargs,
        )
        self._client = self.httpx_client  # type: ignore
        self.http_session = self.httpx_client  # type: ignore

        logger.info(f"Opened httpx client for VespaAsync with configured HTTP version: {self.http_version}")
        logger.info(f"Client details: {self.httpx_client}")

        return self.httpx_client  # type: ignore

    async def make_test_request(self) -> httpx.Response | None:
        """Make a test request to check the actual HTTP version if possible.

        Returns:
            httpx.Response | None: The response object if successful, None otherwise
        """
        if self.httpx_client is None:
            self._open_httpx_client()

        client = self.httpx_client
        if client is None:
            logger.warning("Failed to initialize httpx client")
            return None

        try:
            test_url = f"{self.app.end_point}/status"
            test_response = await client.get(test_url)
            self.last_response_headers = dict(test_response.headers)
            logger.info(f"Async test request made to {test_url}")
            logger.info(f"Response status: {test_response.status_code}")
            logger.info(f"Response headers: {test_response.headers}")
            if "Via" in test_response.headers:
                logger.info(f"Via header: {test_response.headers['Via']}")
            if hasattr(test_response, "http_version"):
                logger.info(f"HTTP version from response: {test_response.http_version}")
        except Exception as e:
            logger.warning(f"Failed to make async test request: {e}")
            return None
        else:
            return test_response

    def get_http_version(self) -> str:
        """Return the HTTP version being used by this client.

        Returns:
            str: Detailed information about the HTTP version configuration and status
        """
        if self.httpx_client is None:
            return f"Configured to use {self.http_version}, but client is not initialized yet"

        headers_info = ""
        if self.last_response_headers:
            headers_info = f", Last response headers: {self.last_response_headers}"

        return f"Configured to use {self.http_version}{headers_info}"

    async def close(self) -> None:
        """Close internal HTTP client."""
        if self.httpx_client is not None:
            await self.httpx_client.aclose()
            self.httpx_client = None
            self._client = None  # type: ignore
            self.http_session = None  # type: ignore


class VespaAdapter(VespaPort):
    """Concrete implementation of the VespaPort interface using pyvespa library.

    This implementation provides a standardized way to interact with Vespa AI,
    abstracting the underlying client implementation details. It uses the VespaSync
    class from vespa.application for synchronous operations.
    """

    def __init__(self, vespa_config: VespaConfig | None = None) -> None:
        """Initialize the VespaAdapter with configuration settings.

        Args:
            vespa_config (VespaConfig, optional): Configuration settings for Vespa.
                If None, retrieves from global config. Defaults to None.
        """
        configs: VespaConfig = BaseConfig.global_config().VESPA if vespa_config is None else vespa_config
        self.vespa_app = self._get_vespa_app(configs)
        self.configs = configs

    def get_http_version(self) -> str:
        """Return the HTTP version being used by this adapter.

        Returns:
            str: Detailed information about the HTTP version configuration and status
        """
        with self._get_sync_client() as client:
            if hasattr(client, "get_http_version"):
                return client.get_http_version()

        return f"Configured to use {self.configs.HTTP_VERSION}"

    def check_actual_http_version(self) -> dict[str, str] | None:
        """Make a test request to check the actual HTTP version being used.

        This method makes a test request to the Vespa server and logs information
        about the HTTP version being used.

        Returns:
            dict[str, str] | None: The response headers from the test request, or None if the request failed
        """
        try:
            with self._get_sync_client() as client:
                if hasattr(client, "last_response_headers") and client.last_response_headers:
                    logger.info(f"Using cached response headers: {client.last_response_headers}")
                    return client.last_response_headers

                test_url = f"{self.vespa_app.url}/status"
                logger.info(f"Making test request to {test_url}")
                if client.httpx_client is None:
                    logger.warning("httpx_client is None, cannot make test request")
                    return None
                response = client.httpx_client.get(test_url)
                headers = dict(response.headers)
                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response headers: {headers}")
                return headers
        except Exception as e:
            logger.warning(f"Failed to check actual HTTP version: {e}")
            return None

    @staticmethod
    def _get_vespa_app(configs: VespaConfig) -> Vespa:
        """Create a Vespa application instance with the specified configuration.

        Args:
            configs (VespaConfig): Configuration settings for Vespa.

        Returns:
            Vespa: Configured Vespa application instance.
        """
        url = f"{'https' if configs.USE_TLS else 'http'}://{configs.HOST}:{configs.PORT}"

        cert = configs.CERT_PATH
        key = configs.KEY_PATH
        token = configs.AUTH_TOKEN

        vespa_app = Vespa(url=url, cert=cert, key=key, vespa_cloud_secret_token=token)

        return vespa_app

    @contextmanager
    def _get_sync_client(self) -> Generator[CustomVespaSync, None, None]:
        """Get a synchronous Vespa client with configurable HTTP version.

        Yields:
            CustomVespaSync: A synchronous Vespa client with HTTP version configuration.
        """
        client = CustomVespaSync(
            app=self.vespa_app,
            http_version=self.configs.HTTP_VERSION,
        )
        try:
            client._open_httpx_client()
            yield client
        finally:
            client.close()

    @override
    def query(
        self,
        query_string: str,
        document_type: VespaDocumentTypeType,
        **kwargs: object,
    ) -> VespaResponseType:
        """Query documents in Vespa.

        Args:
            query_string (str): The YQL query string.
            document_type (VespaDocumentTypeType): The document type to query.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The query results.
        """
        try:
            params = {
                "yql": query_string,
                **kwargs,
            }

            if document_type is not None:
                params["type"] = document_type

            with self._get_sync_client() as sync_client:
                response = sync_client.query(params)
        except Exception:
            logger.exception("Error querying Vespa")
            raise
        else:
            return response

    @override
    def feed(
        self,
        document: VespaDocumentType,
        document_id: VespaIdType,
        document_type: VespaDocumentTypeType,
        **kwargs: object,
    ) -> VespaResponseType:
        """Feed a document to Vespa.

        Args:
            document (VespaDocumentType): The document to feed.
            document_id (VespaIdType): The document ID.
            document_type (VespaDocumentTypeType): The document type.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.
        """
        try:
            fields = document

            with self._get_sync_client() as sync_client:
                schema = kwargs.pop("schema", document_type)
                data_id = kwargs.pop("data_id", document_id)
                fields_param = kwargs.pop("fields", fields)

                schema_str = str(schema)
                data_id_str = str(data_id)
                if fields_param is None:
                    fields_dict = {}
                elif isinstance(fields_param, dict):
                    fields_dict = fields_param
                else:
                    try:
                        fields_dict = dict(fields_param)  # type: ignore
                    except (TypeError, ValueError):
                        logger.warning(f"Could not convert fields_param to dict: {fields_param}")
                        fields_dict = {}

                response = sync_client.feed_data_point(schema_str, data_id_str, fields_dict)
        except Exception:
            logger.exception("Error feeding document to Vespa")
            raise
        else:
            return response

    @override
    def delete(
        self,
        document_id: VespaIdType,
        document_type: VespaDocumentTypeType,
        **kwargs: object,
    ) -> VespaResponseType:
        """Delete a document from Vespa.

        Args:
            document_id (VespaIdType): The document ID.
            document_type (VespaDocumentTypeType): The document type.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.
        """
        try:
            with self._get_sync_client() as sync_client:
                schema = kwargs.pop("schema", document_type)
                data_id = kwargs.pop("data_id", document_id)

                schema_str = str(schema)
                data_id_str = str(data_id)

                response = sync_client.delete_data(schema_str, data_id_str)
        except Exception:
            logger.exception("Error deleting document from Vespa")
            raise
        else:
            return response

    @override
    def get(
        self,
        document_id: VespaIdType,
        document_type: VespaDocumentTypeType,
        **kwargs: object,
    ) -> VespaResponseType:
        """Get a document from Vespa.

        Args:
            document_id (VespaIdType): The document ID.
            document_type (VespaDocumentTypeType): The document type.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The document if found.
        """
        try:
            with self._get_sync_client() as sync_client:
                schema = kwargs.pop("schema", document_type)
                data_id = kwargs.pop("data_id", document_id)

                schema_str = str(schema)
                data_id_str = str(data_id)

                response = sync_client.get_data(schema_str, data_id_str)
        except Exception:
            logger.exception("Error getting document from Vespa")
            raise
        else:
            return response

    @override
    def update(
        self,
        document_id: VespaIdType,
        document_type: VespaDocumentTypeType,
        update_dict: dict[str, Any],
        **kwargs: object,
    ) -> VespaResponseType:
        """Update a document in Vespa.

        Args:
            document_id (VespaIdType): The document ID.
            document_type (VespaDocumentTypeType): The document type.
            update_dict (Dict[str, Any]): The update dictionary.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.
        """
        try:
            with self._get_sync_client() as sync_client:
                schema = kwargs.pop("schema", document_type)
                data_id = kwargs.pop("data_id", document_id)
                fields = kwargs.pop("fields", update_dict)

                schema_str = str(schema)
                data_id_str = str(data_id)
                if fields is None:
                    fields_dict = {}
                elif isinstance(fields, dict):
                    fields_dict = fields
                else:
                    try:
                        fields_dict = dict(fields)  # type: ignore
                    except (TypeError, ValueError):
                        logger.warning(f"Could not convert fields to dict: {fields}")
                        fields_dict = {}

                response = sync_client.update_data(schema_str, data_id_str, fields_dict)
        except Exception:
            logger.exception("Error updating document in Vespa")
            raise
        else:
            return response

    @override
    def create_schema(
        self,
        schema: VespaSchemaType,
        **kwargs: object,
    ) -> VespaResponseType:
        """Create a schema in Vespa.

        Args:
            schema (VespaSchemaType): The schema definition.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.
        """
        try:
            logger.warning("Schema creation via API is not supported by pyvespa. Use deploy() instead.")
        except Exception:
            logger.exception("Error creating schema in Vespa")
            raise
        else:
            return {
                "status": "not_supported",
                "message": "Schema creation via API is not supported by pyvespa. Use deploy() instead.",
            }

    @override
    def delete_schema(
        self,
        schema_name: str,
        **kwargs: object,
    ) -> VespaResponseType:
        """Delete a schema from Vespa.

        Args:
            schema_name (str): The schema name.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.
        """
        try:
            logger.warning("Schema deletion via API is not supported by pyvespa. Use deploy() instead.")
        except Exception:
            logger.exception("Error deleting schema from Vespa")
            raise
        else:
            return {
                "status": "not_supported",
                "message": "Schema deletion via API is not supported by pyvespa. Use deploy() instead.",
            }

    @override
    def get_schema(
        self,
        schema_name: str,
        **kwargs: object,
    ) -> VespaResponseType:
        """Get a schema from Vespa.

        Args:
            schema_name (str): The schema name.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The schema if found.
        """
        try:
            import requests

            url = f"{'https' if self.configs.USE_TLS else 'http'}://{self.configs.HOST}:{self.configs.PORT}/schema/{schema_name}"

            headers = {}
            if self.configs.AUTH_TOKEN:
                headers["Authorization"] = f"Bearer {self.configs.AUTH_TOKEN}"

            response = requests.get(url, headers=headers, timeout=self.configs.TIMEOUT)
            response.raise_for_status()
        except Exception:
            logger.exception("Error getting schema from Vespa")
            raise
        else:
            return response.json()

    @override
    def deploy(
        self,
        **kwargs: object,
    ) -> VespaResponseType:
        """Deploy the application to Vespa.

        This method supports deploying to both Vespa Docker and Vespa Cloud environments.

        Args:
            **kwargs (object): Additional keyword arguments passed to the Vespa client.
                - deployment_type (str): Type of deployment, either "docker" or "cloud". Default is "docker".
                - application_package (ApplicationPackage): The application package to deploy.
                - max_wait_configserver (int): Maximum time to wait for config server to start (Docker only).
                - max_wait_deployment (int): Maximum time to wait for deployment to complete (Docker only).
                - max_wait_docker (int): Maximum time to wait for Docker container to start (Docker only).
                - debug (bool): Whether to enable debug mode (Docker only).
                - application_name (str): Name of the application (Docker only).
                - application_root (Path): Path to the application root directory (Docker only).
                - instance (str): Instance name (Cloud only).
                - disk_folder (str): Path to the disk folder (Cloud only).
                - version (str): Version to deploy (Cloud only).
                - max_wait (int): Maximum time to wait for deployment to complete (Cloud only).

        Returns:
            VespaResponseType: The response from Vespa.
        """
        try:
            deployment_type = str(kwargs.get("deployment_type", "docker"))

            application_package = kwargs.get("application_package")
            if application_package is None and hasattr(self.vespa_app, "_application_package"):
                application_package = self.vespa_app._application_package

            if application_package is None:
                logger.warning("Application deployment requires an application package.")
                return {"status": "error", "message": "Application deployment requires an application package."}

            if deployment_type.lower() == "docker":
                from vespa.deployment import VespaDocker

                container_name = kwargs.get("container_name")

                if container_name:
                    container_name_str = str(container_name)
                    logger.info(f"Using existing Vespa container: {container_name_str}")
                    docker_instance = VespaDocker.from_container_name_or_id(container_name_str)
                else:
                    docker_instance = VespaDocker(port=self.configs.PORT)

                logger.info(f"Deploying application package to Docker: {application_package}")

                app_package = application_package
                if isinstance(app_package, ApplicationPackage):
                    return docker_instance.deploy(
                        application_package=app_package,
                        max_wait_configserver=200,
                        max_wait_deployment=300,
                        max_wait_docker=300,
                    )
                else:
                    logger.warning(f"Expected ApplicationPackage type, got {type(app_package)}. Deployment may fail.")
                    try:
                        app_package_cast = cast(ApplicationPackage, app_package)
                        return docker_instance.deploy(
                            application_package=app_package_cast,
                            max_wait_configserver=200,
                            max_wait_deployment=300,
                            max_wait_docker=300,
                        )
                    except Exception as e:
                        logger.exception("Failed to deploy")
                        return {"status": "error", "message": f"Failed to deploy: {e}"}

            elif deployment_type.lower() == "cloud":
                from vespa.deployment import VespaCloud

                if self.configs.TENANT_NAME is None or self.configs.APPLICATION_NAME is None:
                    logger.error("VespaCloud deployment requires TENANT_NAME and APPLICATION_NAME to be set")
                    return {
                        "status": "error",
                        "message": "VespaCloud deployment requires TENANT_NAME and APPLICATION_NAME to be set",
                    }

                tenant_name = str(self.configs.TENANT_NAME)
                app_name = str(self.configs.APPLICATION_NAME)
                key_path = str(self.configs.KEY_PATH) if self.configs.KEY_PATH is not None else None
                auth_token = str(self.configs.AUTH_TOKEN) if self.configs.AUTH_TOKEN is not None else None

                app_package = application_package
                if app_package is not None and not isinstance(app_package, ApplicationPackage):
                    logger.warning(f"Expected ApplicationPackage type, got {type(app_package)}. Deployment may fail.")
                    try:
                        app_package = cast(ApplicationPackage, app_package)
                    except Exception as e:
                        logger.exception(f"Failed to cast application_package: {e}")
                        return {"status": "error", "message": f"Failed to cast application_package: {e}"}

                try:
                    cloud_instance = VespaCloud(
                        tenant=tenant_name,
                        application=app_name,
                        application_package=app_package,
                        key_location=key_path,
                        auth_client_token_id=auth_token,
                    )
                except Exception as e:
                    logger.exception(f"Failed to create VespaCloud instance: {e}")
                    return {"status": "error", "message": f"Failed to create VespaCloud instance: {e}"}

                instance = str(kwargs.get("instance", "default"))
                disk_folder = kwargs.get("disk_folder")
                if disk_folder is not None:
                    disk_folder = str(disk_folder)
                version = kwargs.get("version")
                if version is not None:
                    version = str(version)
                max_wait_value = kwargs.get("max_wait", 1800)
                if isinstance(max_wait_value, int | float | str):
                    max_wait = int(max_wait_value)
                else:
                    max_wait = 1800

                return cloud_instance.deploy(
                    instance=instance,
                    disk_folder=disk_folder,
                    version=version,
                    max_wait=max_wait,
                )

            else:
                logger.warning(f"Unknown deployment type: {deployment_type}. Falling back to basic deployment.")
                logger.warning("Basic deployment not supported directly. Using application package if available.")
                if hasattr(self.vespa_app, "_application_package") and self.vespa_app._application_package is not None:
                    return {"status": "success", "message": "Used application package for deployment"}
                return {"status": "error", "message": "No deployment method available for this configuration"}

        except Exception:
            logger.exception("Error deploying application to Vespa")
            raise


class AsyncVespaAdapter(AsyncVespaPort):
    """Concrete implementation of the AsyncVespaPort interface using pyvespa library.

    This implementation provides a standardized way to interact with Vespa AI asynchronously,
    abstracting the underlying client implementation details. It uses the VespaAsync
    class from vespa.application for asynchronous operations.
    """

    def __init__(self, vespa_config: VespaConfig | None = None) -> None:
        """Initialize the AsyncVespaAdapter with configuration settings.

        Args:
            vespa_config (VespaConfig, optional): Configuration settings for Vespa.
                If None, retrieves from global config. Defaults to None.
        """
        configs: VespaConfig = BaseConfig.global_config().VESPA if vespa_config is None else vespa_config
        self.vespa_app = self._get_vespa_app(configs)
        self.configs = configs

    def get_http_version(self) -> str:
        """Return the HTTP version being used by this adapter.

        Returns:
            str: Detailed information about the HTTP version configuration and status
        """
        return self.vespa_app.get_http_version()

    async def check_actual_http_version(self) -> dict[str, str] | None:
        """Make a test request to check the actual HTTP version being used.

        This method makes a test request to the Vespa server and logs information
        about the HTTP version being used.

        Returns:
            dict[str, str] | None: The response headers from the test request, or None if the request failed
        """
        try:
            response = await self.vespa_app.make_test_request()
            if response:
                logger.info("Actual HTTP version check completed successfully")
                return dict(response.headers) if hasattr(response, "headers") else None
        except Exception as e:
            logger.warning(f"Failed to check actual HTTP version: {e}")

        return None

    @staticmethod
    def _get_vespa_app(configs: VespaConfig) -> CustomVespaAsync:
        """Create a CustomVespaAsync instance with the specified configuration.

        Args:
            configs (VespaConfig): Configuration settings for Vespa.

        Returns:
            CustomVespaAsync: Configured CustomVespaAsync instance.
        """
        url = f"{'https' if configs.USE_TLS else 'http'}://{configs.HOST}:{configs.PORT}"

        cert = configs.CERT_PATH
        key = configs.KEY_PATH
        token = configs.AUTH_TOKEN

        vespa_app = Vespa(url=url, cert=cert, key=key, vespa_cloud_secret_token=token)

        vespa_async = CustomVespaAsync(
            app=vespa_app,
            http_version=configs.HTTP_VERSION,
            timeout=configs.TIMEOUT,
        )

        return vespa_async

    @override
    async def query(
        self,
        query_string: str,
        document_type: VespaDocumentTypeType,
        **kwargs: object,
    ) -> VespaResponseType:
        """Query documents in Vespa.

        Args:
            query_string (str): The YQL query string.
            document_type (VespaDocumentTypeType): The document type to query.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The query results.
        """
        try:
            self.vespa_app._open_httpx_client()

            params = {
                "yql": query_string,
                **kwargs,
            }
            if document_type is not None:
                params["type"] = document_type

            response = await self.vespa_app.query(params)
        except Exception:
            logger.exception("Error querying Vespa asynchronously")
            raise
        else:
            return response

    @override
    async def feed(
        self,
        document: VespaDocumentType,
        document_id: VespaIdType,
        document_type: VespaDocumentTypeType,
        **kwargs: object,
    ) -> VespaResponseType:
        """Feed a document to Vespa.

        Args:
            document (VespaDocumentType): The document to feed.
            document_id (VespaIdType): The document ID.
            document_type (VespaDocumentTypeType): The document type.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.
        """
        try:
            self.vespa_app._open_httpx_client()

            fields = document

            schema = kwargs.pop("schema", document_type)
            data_id = kwargs.pop("data_id", document_id)
            fields_param = kwargs.pop("fields", fields)

            schema_str = str(schema)
            data_id_str = str(data_id)
            if fields_param is None:
                fields_dict = {}
            elif isinstance(fields_param, dict):
                fields_dict = fields_param
            else:
                try:
                    fields_dict = dict(fields_param)  # type: ignore
                except (TypeError, ValueError):
                    logger.warning(f"Could not convert fields_param to dict: {fields_param}")
                    fields_dict = {}

            response = await self.vespa_app.feed_data_point(schema_str, data_id_str, fields_dict)
        except Exception:
            logger.exception("Error feeding document to Vespa asynchronously")
            raise
        else:
            return response

    @override
    async def delete(
        self,
        document_id: VespaIdType,
        document_type: VespaDocumentTypeType,
        **kwargs: object,
    ) -> VespaResponseType:
        """Delete a document from Vespa.

        Args:
            document_id (VespaIdType): The document ID.
            document_type (VespaDocumentTypeType): The document type.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.
        """
        try:
            self.vespa_app._open_httpx_client()

            schema = kwargs.pop("schema", document_type)
            data_id = kwargs.pop("data_id", document_id)

            schema_str = str(schema)
            data_id_str = str(data_id)

            response = await self.vespa_app.delete_data(schema_str, data_id_str)
        except Exception:
            logger.exception("Error deleting document from Vespa asynchronously")
            raise
        else:
            return response

    @override
    async def get(
        self,
        document_id: VespaIdType,
        document_type: VespaDocumentTypeType,
        **kwargs: object,
    ) -> VespaResponseType:
        """Get a document from Vespa.

        Args:
            document_id (VespaIdType): The document ID.
            document_type (VespaDocumentTypeType): The document type.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The document if found.
        """
        try:
            self.vespa_app._open_httpx_client()

            schema = kwargs.pop("schema", document_type)
            data_id = kwargs.pop("data_id", document_id)

            schema_str = str(schema)
            data_id_str = str(data_id)

            response = await self.vespa_app.get_data(schema_str, data_id_str)
        except Exception:
            logger.exception("Error getting document from Vespa asynchronously")
            raise
        else:
            return response

    @override
    async def update(
        self,
        document_id: VespaIdType,
        document_type: VespaDocumentTypeType,
        update_dict: dict[str, Any],
        **kwargs: object,
    ) -> VespaResponseType:
        """Update a document in Vespa.

        Args:
            document_id (VespaIdType): The document ID.
            document_type (VespaDocumentTypeType): The document type.
            update_dict (Dict[str, Any]): The update dictionary.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.
        """
        try:
            self.vespa_app._open_httpx_client()

            schema = kwargs.pop("schema", document_type)
            data_id = kwargs.pop("data_id", document_id)
            fields = kwargs.pop("fields", update_dict)

            schema_str = str(schema)
            data_id_str = str(data_id)
            if fields is None:
                fields_dict = {}
            elif isinstance(fields, dict):
                fields_dict = fields
            else:
                try:
                    fields_dict = dict(fields)  # type: ignore
                except (TypeError, ValueError):
                    logger.warning(f"Could not convert fields to dict: {fields}")
                    fields_dict = {}

            response = await self.vespa_app.update_data(schema_str, data_id_str, fields_dict)
        except Exception:
            logger.exception("Error updating document in Vespa asynchronously")
            raise
        else:
            return response

    @override
    async def create_schema(
        self,
        schema: VespaSchemaType,
        **kwargs: object,
    ) -> VespaResponseType:
        """Create a schema in Vespa.

        Args:
            schema (VespaSchemaType): The schema definition.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.
        """
        try:
            logger.warning("Schema creation via API is not supported by pyvespa. Use deploy() instead.")
        except Exception:
            logger.exception("Error creating schema in Vespa asynchronously")
            raise
        else:
            return {
                "status": "not_supported",
                "message": "Schema creation via API is not supported by pyvespa. Use deploy() instead.",
            }

    @override
    async def delete_schema(
        self,
        schema_name: str,
        **kwargs: object,
    ) -> VespaResponseType:
        """Delete a schema from Vespa.

        Args:
            schema_name (str): The schema name.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.
        """
        try:
            logger.warning("Schema deletion via API is not supported by pyvespa. Use deploy() instead.")
        except Exception:
            logger.exception("Error deleting schema from Vespa asynchronously")
            raise
        else:
            return {
                "status": "not_supported",
                "message": "Schema deletion via API is not supported by pyvespa. Use deploy() instead.",
            }

    @override
    async def get_schema(
        self,
        schema_name: str,
        **kwargs: object,
    ) -> VespaResponseType:
        """Get a schema from Vespa.

        Args:
            schema_name (str): The schema name.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The schema if found.
        """
        try:
            vespa_app = cast(Any, self.vespa_app)
            client = vespa_app._open_httpx_client()

            if client is None:
                raise RuntimeError("Failed to initialize HTTP client")

            url = f"{self.vespa_app.app.end_point}/schema/{schema_name}"

            if self.vespa_app._client is None:
                raise RuntimeError("HTTP client is not initialized")

            response = await self.vespa_app._client.get(url)
            response.raise_for_status()
        except Exception:
            logger.exception("Error getting schema from Vespa asynchronously")
            raise
        else:
            return response.json()

    @override
    async def deploy(
        self,
        **kwargs: object,
    ) -> VespaResponseType:
        """Deploy the application to Vespa asynchronously.

        This method supports deploying to both Vespa Docker and Vespa Cloud environments.

        Args:
            **kwargs (object): Additional keyword arguments passed to the Vespa client.
                - deployment_type (str): Type of deployment, either "docker" or "cloud". Default is "docker".
                - application_package (ApplicationPackage): The application package to deploy.
                - max_wait_configserver (int): Maximum time to wait for config server to start (Docker only).
                - max_wait_deployment (int): Maximum time to wait for deployment to complete (Docker only).
                - max_wait_docker (int): Maximum time to wait for Docker container to start (Docker only).
                - debug (bool): Whether to enable debug mode (Docker only).
                - application_name (str): Name of the application (Docker only).
                - application_root (Path): Path to the application root directory (Docker only).
                - instance (str): Instance name (Cloud only).
                - disk_folder (str): Path to the disk folder (Cloud only).
                - version (str): Version to deploy (Cloud only).
                - max_wait (int): Maximum time to wait for deployment to complete (Cloud only).

        Returns:
            VespaResponseType: The response from Vespa.
        """
        try:
            deployment_type = str(kwargs.get("deployment_type", "docker"))

            application_package = kwargs.get("application_package")
            if application_package is None and hasattr(self.vespa_app.app, "_application_package"):
                application_package = self.vespa_app.app._application_package

            if application_package is None:
                logger.warning("Application deployment requires an application package.")
                return {"status": "error", "message": "Application deployment requires an application package."}

            import asyncio

            if deployment_type.lower() == "docker":
                from vespa.deployment import VespaDocker

                container_name = kwargs.get("container_name")
                if container_name:
                    container_name_str = str(container_name)
                    logger.info(f"Using existing Vespa container: {container_name_str}")
                    docker_instance = VespaDocker.from_container_name_or_id(container_name_str)
                else:
                    docker_instance = VespaDocker(port=self.configs.PORT)

                logger.info(f"Deploying application package to Docker asynchronously: {application_package}")

                max_wait_configserver_value = kwargs.get("max_wait_configserver", 120)
                if isinstance(max_wait_configserver_value, int | float | str):
                    max_wait_configserver = int(max_wait_configserver_value)
                else:
                    max_wait_configserver = 120

                max_wait_deployment_value = kwargs.get("max_wait_deployment", 300)
                if isinstance(max_wait_deployment_value, int | float | str):
                    max_wait_deployment = int(max_wait_deployment_value)
                else:
                    max_wait_deployment = 300

                max_wait_docker_value = kwargs.get("max_wait_docker", 300)
                if isinstance(max_wait_docker_value, int | float | str):
                    max_wait_docker = int(max_wait_docker_value)
                else:
                    max_wait_docker = 300

                debug = bool(kwargs.get("debug", True))

                if not isinstance(application_package, ApplicationPackage):
                    logger.warning(
                        f"Expected ApplicationPackage type, got {type(application_package)}. Deployment may fail.",
                    )
                    try:
                        app_package = cast(ApplicationPackage, application_package)
                    except Exception as e:
                        logger.exception(f"Failed to cast application_package: {e}")
                        return {"status": "error", "message": f"Failed to cast application_package: {e}"}
                else:
                    app_package = application_package

                return await asyncio.to_thread(
                    docker_instance.deploy,
                    application_package=app_package,
                    max_wait_configserver=max_wait_configserver,
                    max_wait_deployment=max_wait_deployment,
                    max_wait_docker=max_wait_docker,
                    debug=debug,
                )

            elif deployment_type.lower() == "cloud":
                from vespa.deployment import VespaCloud

                if self.configs.TENANT_NAME is None or self.configs.APPLICATION_NAME is None:
                    logger.error("VespaCloud deployment requires TENANT_NAME and APPLICATION_NAME to be set")
                    return {
                        "status": "error",
                        "message": "VespaCloud deployment requires TENANT_NAME and APPLICATION_NAME to be set",
                    }

                tenant_name = str(self.configs.TENANT_NAME)
                app_name = str(self.configs.APPLICATION_NAME)
                key_path = str(self.configs.KEY_PATH) if self.configs.KEY_PATH is not None else None
                auth_token = str(self.configs.AUTH_TOKEN) if self.configs.AUTH_TOKEN is not None else None

                app_package = application_package
                if app_package is not None and not isinstance(app_package, ApplicationPackage):
                    logger.warning(f"Expected ApplicationPackage type, got {type(app_package)}. Deployment may fail.")
                    try:
                        app_package = cast(ApplicationPackage, app_package)
                    except Exception as e:
                        logger.exception(f"Failed to cast application_package: {e}")
                        return {"status": "error", "message": f"Failed to cast application_package: {e}"}

                try:
                    cloud_instance = VespaCloud(
                        tenant=tenant_name,
                        application=app_name,
                        application_package=app_package,
                        key_location=key_path,
                        auth_client_token_id=auth_token,
                    )
                except Exception as e:
                    logger.exception(f"Failed to create VespaCloud instance: {e}")
                    return {"status": "error", "message": f"Failed to create VespaCloud instance: {e}"}

                instance = str(kwargs.get("instance", "default"))
                disk_folder = kwargs.get("disk_folder")
                if disk_folder is not None:
                    disk_folder = str(disk_folder)
                version = kwargs.get("version")
                if version is not None:
                    version = str(version)
                max_wait_value = kwargs.get("max_wait", 1800)
                if isinstance(max_wait_value, int | float | str):
                    max_wait = int(max_wait_value)
                else:
                    max_wait = 1800

                return await asyncio.to_thread(
                    cloud_instance.deploy,
                    instance=instance,
                    disk_folder=disk_folder,
                    version=version,
                    max_wait=max_wait,
                )

            else:
                logger.warning(f"Unknown deployment type: {deployment_type}. Falling back to basic deployment.")
                logger.warning("Basic deployment not supported directly. Using application package if available.")
                if (
                    hasattr(self.vespa_app.app, "_application_package")
                    and self.vespa_app.app._application_package is not None
                ):
                    return {"status": "success", "message": "Used application package for deployment"}
                return {"status": "error", "message": "No deployment method available for this configuration"}

        except Exception:
            logger.exception("Error deploying application to Vespa asynchronously")
            raise

    async def __aenter__(self) -> "AsyncVespaAdapter":
        """Enter the async context manager.

        Returns:
            AsyncVespaAdapter: This adapter instance.
        """
        vespa_app = cast(Any, self.vespa_app)
        await vespa_app.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit the async context manager.

        Closes the VespaAsync instance.

        Args:
            exc_type: The exception type, if an exception was raised
            exc_val: The exception value, if an exception was raised
            exc_tb: The traceback, if an exception was raised
        """
        vespa_app = cast(Any, self.vespa_app)
        await vespa_app.__aexit__(exc_type, exc_val, exc_tb)
