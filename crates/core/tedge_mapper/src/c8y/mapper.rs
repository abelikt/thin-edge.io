use crate::{
    c8y::converter::CumulocityConverter,
    core::{component::TEdgeComponent, mapper::create_mapper, size_threshold::SizeThreshold},
};

use agent_interface::topic::ResponseTopic;
use async_trait::async_trait;
use c8y_api::http_proxy::{C8YHttpProxy, JwtAuthHttpProxy};
use c8y_smartrest::operations::Operations;
use mqtt_channel::TopicFilter;
use tedge_config::{
    ConfigSettingAccessor, DeviceIdSetting, DeviceTypeSetting, MqttBindAddressSetting,
    MqttPortSetting, TEdgeConfig,
};
use tedge_utils::file::*;
use tracing::{info, info_span, Instrument};

use super::topic::C8yTopic;

const CUMULOCITY_MAPPER_NAME: &str = "tedge-mapper-c8y";
const MQTT_MESSAGE_SIZE_THRESHOLD: usize = 16184;

pub struct CumulocityMapper {}

impl CumulocityMapper {
    pub fn new() -> CumulocityMapper {
        CumulocityMapper {}
    }

    pub fn subscriptions(operations: &Operations) -> Result<TopicFilter, anyhow::Error> {
        let mut topic_filter = TopicFilter::new(ResponseTopic::SoftwareListResponse.as_str())?;
        topic_filter.add(ResponseTopic::SoftwareUpdateResponse.as_str())?;
        topic_filter.add(C8yTopic::SmartRestRequest.as_str())?;
        topic_filter.add(ResponseTopic::RestartResponse.as_str())?;

        for topic in operations.topics_for_operations() {
            topic_filter.add(&topic)?
        }

        Ok(topic_filter)
    }
}

#[async_trait]
impl TEdgeComponent for CumulocityMapper {
    fn session_name(&self) -> &str {
        CUMULOCITY_MAPPER_NAME
    }

    async fn init(&self) -> Result<(), anyhow::Error> {
        info!("Initialize tedge mapper c8y");
        create_directories()?;
        let operations = Operations::try_new("/etc/tedge/operations", "c8y")?;
        self.init_session(CumulocityMapper::subscriptions(&operations)?)
            .await?;
        Ok(())
    }

    async fn start(&self, tedge_config: TEdgeConfig) -> Result<(), anyhow::Error> {
        let size_threshold = SizeThreshold(MQTT_MESSAGE_SIZE_THRESHOLD);

        let operations = Operations::try_new("/etc/tedge/operations", "c8y")?;
        let mut http_proxy = JwtAuthHttpProxy::try_new(&tedge_config).await?;
        http_proxy.init().await?;
        let device_name = tedge_config.query(DeviceIdSetting)?;
        let device_type = tedge_config.query(DeviceTypeSetting)?;
        let mqtt_port = tedge_config.query(MqttPortSetting)?.into();
        let mqtt_host = tedge_config.query(MqttBindAddressSetting)?.to_string();

        let converter = Box::new(CumulocityConverter::new(
            size_threshold,
            device_name,
            device_type,
            operations,
            http_proxy,
        ));

        let mut mapper =
            create_mapper(CUMULOCITY_MAPPER_NAME, mqtt_host, mqtt_port, converter).await?;

        mapper
            .run()
            .instrument(info_span!(CUMULOCITY_MAPPER_NAME))
            .await?;

        Ok(())
    }
}

fn create_directories() -> Result<(), anyhow::Error> {
    create_directory_with_user_group(
        "/etc/tedge/operations/c8y",
        "tedge-mapper",
        "tedge-mapper",
        0o775,
    )?;
    create_file_with_user_group(
        "/etc/tedge/operations/c8y/c8y_SoftwareUpdate",
        "tedge-mapper",
        "tedge-mapper",
        0o644,
    )?;
    create_file_with_user_group(
        "/etc/tedge/operations/c8y/c8y_Restart",
        "tedge-mapper",
        "tedge-mapper",
        0o644,
    )?;
    Ok(())
}
