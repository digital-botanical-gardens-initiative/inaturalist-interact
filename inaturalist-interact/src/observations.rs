use inaturalist::apis::configuration;
use inaturalist::apis::observations_api::{observations_id_get, ObservationsIdGetParams};
use std::error::Error;

/// Fetches an observation from the iNaturalist API based on the given observation ID.
///
/// # Arguments
///
/// * `observation_id` - The ID of the observation to fetch.
///
/// # Returns
///
/// This function returns a `Result` which is either the raw JSON string on success
/// or an error on failure.
pub async fn get_observation(observation_id: i32) -> Result<String, Box<dyn Error>> {
    let mut config = configuration::Configuration::default();
    config.base_path = "https://api.inaturalist.org/v1".to_string();

    let observation_params = ObservationsIdGetParams {
        id: vec![observation_id],
    };

    let response = observations_id_get(&config, observation_params).await?;
    let raw_json = serde_json::to_string(&response)?;
    Ok(raw_json)
}
