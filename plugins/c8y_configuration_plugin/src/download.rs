use crate::error::ConfigManagementError;
use crate::smartrest::TryIntoOperationStatusMessage;
use crate::{error, PluginConfig};
use c8y_api::http_proxy::{C8YHttpProxy, JwtAuthHttpProxy};
use c8y_smartrest::error::SmartRestSerializerError;
use c8y_smartrest::smartrest_deserializer::SmartRestConfigDownloadRequest;
use c8y_smartrest::smartrest_serializer::{
    CumulocitySupportedOperations, SmartRest, SmartRestSerializer,
    SmartRestSetOperationToExecuting, SmartRestSetOperationToFailed,
    SmartRestSetOperationToSuccessful,
};
use download::{Auth, DownloadInfo, Downloader};
use mqtt_channel::{Connection, Message, SinkExt, Topic};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::fs;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};

const CONFIG_CHANGE_TOPIC: &str = "tedge/configuration_change";

pub async fn handle_config_download_request(
    plugin_config: &PluginConfig,
    smartrest_request: SmartRestConfigDownloadRequest,
    tmp_dir: PathBuf,
    mqtt_client: &mut Connection,
    http_client: &mut JwtAuthHttpProxy,
) -> Result<(), anyhow::Error> {
    let executing_message = DownloadConfigFileStatusMessage::executing()?;
    let () = mqtt_client.published.send(executing_message).await?;

    // Add validation if the config_type exists in
    let changed_file = smartrest_request.config_type.clone();

    match download_config_file(plugin_config, smartrest_request, tmp_dir, http_client).await {
        Ok(_) => {
            let successful_message = DownloadConfigFileStatusMessage::successful(None)?;
            let () = mqtt_client.published.send(successful_message).await?;

            let notification_message = get_file_change_notification_message(changed_file);
            let () = mqtt_client.published.send(notification_message).await?;
            Ok(())
        }
        Err(err) => {
            let failed_message = DownloadConfigFileStatusMessage::failed(err.to_string())?;
            let () = mqtt_client.published.send(failed_message).await?;
            Err(err)
        }
    }
}

async fn download_config_file(
    plugin_config: &PluginConfig,
    smartrest_request: SmartRestConfigDownloadRequest,
    tmp_dir: PathBuf,
    http_client: &mut JwtAuthHttpProxy,
) -> Result<(), anyhow::Error> {
    // Convert smartrest request to config download request struct
    let mut config_download_request =
        ConfigDownloadRequest::try_new(smartrest_request, plugin_config, tmp_dir)?;

    // Confirm that the file has write access before any http request attempt
    let () = config_download_request.has_write_access()?;

    // If the provided url is c8y, add auth
    if http_client.url_is_in_my_tenant_domain(config_download_request.download_info.url()) {
        let token = http_client.get_jwt_token().await?;
        config_download_request.download_info.auth = Some(Auth::new_bearer(&token.token()));
    }

    // Download a file to tmp dir
    let downloader = config_download_request.create_downloader();
    let () = downloader
        .download(&config_download_request.download_info)
        .await?;

    // Move the downloaded file to the final destination
    let () = config_download_request.move_file()?;

    Ok(())
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
pub struct ConfigDownloadRequest {
    pub download_info: DownloadInfo,
    pub destination_path: PathBuf,
    pub tmp_dir: PathBuf,
    pub file_name: String,
}

impl ConfigDownloadRequest {
    fn try_new(
        request: SmartRestConfigDownloadRequest,
        plugin_config: &PluginConfig,
        tmp_dir: PathBuf,
    ) -> Result<Self, ConfigManagementError> {
        // Check if the requested config type is in the plugin config list
        let all_file_paths = plugin_config.get_all_file_paths();
        if !all_file_paths.contains(&request.config_type) {
            return Err(ConfigManagementError::InvalidRequestedConfigType {
                path: request.config_type,
            });
        }

        let destination_path = PathBuf::from(request.config_type);
        let file_name = Self::get_filename(destination_path.clone())?;

        Ok(Self {
            download_info: DownloadInfo {
                url: request.url,
                auth: None,
            },
            destination_path,
            tmp_dir,
            file_name,
        })
    }

    fn get_filename(path: PathBuf) -> Result<String, ConfigManagementError> {
        let filename = path
            .file_name()
            .ok_or_else(|| ConfigManagementError::FileNameNotFound { path: path.clone() })?
            .to_str()
            .ok_or_else(|| ConfigManagementError::InvalidFileName { path: path.clone() })?
            .to_string();
        Ok(filename)
    }

    fn has_write_access(&self) -> Result<(), ConfigManagementError> {
        // The file does not exist before downloading a file
        if !&self.destination_path.is_file() {
            return Ok(());
        }
        // Need a permission check when the file exists already
        let metadata = Self::get_metadata(&self.destination_path)?;
        if metadata.permissions().readonly() {
            Err(error::ConfigManagementError::ReadOnlyFile {
                path: self.destination_path.clone(),
            })
        } else {
            Ok(())
        }
    }

    fn create_downloader(&self) -> Downloader {
        Downloader::new(&self.file_name, &None, &self.tmp_dir)
    }

    fn get_metadata(path: &Path) -> Result<std::fs::Metadata, ConfigManagementError> {
        fs::metadata(&path).map_err(|_| ConfigManagementError::FileNotAccessible {
            path: path.to_path_buf(),
        })
    }

    fn move_file(&self) -> Result<(), ConfigManagementError> {
        let src = &self.tmp_dir.join(&self.file_name);
        let dest = &self.destination_path;

        let original_permission_mode = match self.destination_path.is_file() {
            true => {
                let metadata = Self::get_metadata(&self.destination_path)?;
                let mode = metadata.permissions().mode();
                Some(mode)
            }
            false => None,
        };

        let _ = fs::copy(src, dest).map_err(|_| ConfigManagementError::FileCopyFailed {
            src: src.to_path_buf(),
            dest: dest.to_path_buf(),
        })?;

        // Change the file permission back to the original one
        if let Some(mode) = original_permission_mode {
            let mut permissions = Self::get_metadata(&self.destination_path)?.permissions();
            let _ = permissions.set_mode(mode);
            let _ = std::fs::set_permissions(&self.destination_path, permissions);
        }

        Ok(())
    }
}

pub fn get_file_change_notification_message(config_type: String) -> Message {
    let notification = json!({ "changedFile": config_type }).to_string();
    Message::new(&Topic::new_unchecked(CONFIG_CHANGE_TOPIC), notification)
}

struct DownloadConfigFileStatusMessage {}

impl TryIntoOperationStatusMessage for DownloadConfigFileStatusMessage {
    fn status_executing() -> Result<SmartRest, SmartRestSerializerError> {
        SmartRestSetOperationToExecuting::new(CumulocitySupportedOperations::C8yDownloadConfigFile)
            .to_smartrest()
    }

    fn status_successful(
        _parameter: Option<String>,
    ) -> Result<SmartRest, SmartRestSerializerError> {
        SmartRestSetOperationToSuccessful::new(CumulocitySupportedOperations::C8yDownloadConfigFile)
            .to_smartrest()
    }

    fn status_failed(failure_reason: String) -> Result<SmartRest, SmartRestSerializerError> {
        SmartRestSetOperationToFailed::new(
            CumulocitySupportedOperations::C8yDownloadConfigFile,
            failure_reason,
        )
        .to_smartrest()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::FileEntry;
    use assert_matches::*;
    use c8y_smartrest::smartrest_deserializer::SmartRestRequestGeneric;
    use std::collections::HashSet;

    #[test]
    fn create_config_download_request() -> Result<(), anyhow::Error> {
        let payload = "524,rina0005,https://test.cumulocity.com/inventory/binaries/70208,/etc/tedge/tedge.toml";
        let smartrest_request = SmartRestConfigDownloadRequest::from_smartrest(payload)?;
        let plugin_config = PluginConfig {
            files: HashSet::from([
                FileEntry::new("/etc/tedge/tedge.toml".to_string()),
                FileEntry::new("/etc/tedge/mosquitto-conf/c8y-bridge.conf".to_string()),
                FileEntry::new("/etc/tedge/mosquitto-conf/tedge-mosquitto.conf".to_string()),
                FileEntry::new("/etc/mosquitto/mosquitto.conf".to_string()),
            ]),
        };
        let config_download_request = ConfigDownloadRequest::try_new(
            smartrest_request,
            &plugin_config,
            PathBuf::from("/tmp"),
        )?;
        assert_eq!(
            config_download_request,
            ConfigDownloadRequest {
                download_info: DownloadInfo {
                    url: "https://test.cumulocity.com/inventory/binaries/70208".to_string(),
                    auth: None
                },
                destination_path: PathBuf::from("/etc/tedge/tedge.toml"),
                tmp_dir: PathBuf::from("/tmp"),
                file_name: "tedge.toml".to_string()
            }
        );
        Ok(())
    }

    #[test]
    fn requested_config_does_not_match_config_plugin() -> Result<(), anyhow::Error> {
        let payload = "524,rina0005,https://test.cumulocity.com/inventory/binaries/70208,/etc/tedge/not_in_config.toml";
        let smartrest_request = SmartRestConfigDownloadRequest::from_smartrest(payload)?;
        let plugin_config = PluginConfig {
            files: HashSet::from([
                FileEntry::new("/etc/tedge/tedge.toml".to_string()),
                FileEntry::new("/etc/tedge/mosquitto-conf/c8y-bridge.conf".to_string()),
                FileEntry::new("/etc/tedge/mosquitto-conf/tedge-mosquitto.conf".to_string()),
                FileEntry::new("/etc/mosquitto/mosquitto.conf".to_string()),
            ]),
        };
        let config_download_request = ConfigDownloadRequest::try_new(
            smartrest_request,
            &plugin_config,
            PathBuf::from("/tmp"),
        );
        assert_matches!(
            config_download_request,
            Err(ConfigManagementError::InvalidRequestedConfigType { .. })
        );
        Ok(())
    }

    #[test]
    fn get_smartrest_executing() {
        let message = DownloadConfigFileStatusMessage::executing().unwrap();
        assert_eq!(message.topic, Topic::new("c8y/s/us").unwrap());
        assert_eq!(
            message.payload_str().unwrap(),
            "501,c8y_DownloadConfigFile\n"
        );
    }

    #[test]
    fn get_smartrest_successful() {
        let message = DownloadConfigFileStatusMessage::successful(None).unwrap();
        assert_eq!(message.topic, Topic::new("c8y/s/us").unwrap());
        assert_eq!(
            message.payload_str().unwrap(),
            "503,c8y_DownloadConfigFile,\n"
        );
    }

    #[test]
    fn get_smartrest_failed() {
        let message = DownloadConfigFileStatusMessage::failed("failed reason".to_string()).unwrap();
        assert_eq!(message.topic, Topic::new("c8y/s/us").unwrap());
        assert_eq!(
            message.payload_str().unwrap(),
            "502,c8y_DownloadConfigFile,\"failed reason\"\n"
        );
    }
}
