import base64

from app.common.tls import extract_all_certs


class TestExtractAllCerts:
    def test_extract_valid_certs(self, mocker, tmp_path):
        cert_content = b"cert1"
        encoded_cert = base64.b64encode(cert_content).decode()

        cert_path = tmp_path / "cert1.pem"

        mock_named_temp_file = mocker.patch(
            "app.common.tls.tempfile.NamedTemporaryFile"
        )
        mock_file_obj = mocker.MagicMock()
        mock_file_obj.name = str(cert_path)
        mock_named_temp_file.return_value.__enter__.return_value = mock_file_obj

        certs = extract_all_certs({"TRUSTSTORE_CERT1": encoded_cert})

        assert len(certs) == 1
        assert certs["TRUSTSTORE_CERT1"] == str(cert_path)
        mock_file_obj.write.assert_called_once_with(b"cert1")

    def test_extract_invalid_base64_cert(self):
        certs = extract_all_certs({"TRUSTSTORE_BAD": "invalid-base64!"})
        assert len(certs) == 0

    def test_extract_no_truststore_vars(self):
        certs = extract_all_certs({"NORMAL_VAR": "value"})
        assert len(certs) == 0
