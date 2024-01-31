// observations.rs

use inaturalist::apis::configuration;
use inaturalist::apis::observations_api::{observations_id_get, ObservationsIdGetParams};
use reqwest::Error as ReqwestError;

/// Fetches an observation from the iNaturalist API based on the given observation ID.
///
/// # Arguments
///
/// * `observation_id` - The ID of the observation to fetch.
///
/// # Returns
///
/// This function returns a `Result` which is either the fetched observation on success
/// or an error on failure.
pub async fn get_observation(observation_id: i32) -> Result<String, ReqwestError> {
    let mut config = configuration::Configuration::default();
    
    // Set the base URL for the API
    config.base_path = "https://api.inaturalist.org/v1".to_string();

    let observation_params = ObservationsIdGetParams {
        id: vec![observation_id],
    };

    match observations_id_get(&config, observation_params).await {
        Ok(response) => Ok(format!("Observation Response: {:?}", response)),
        Err(e) => Err(e),
    }
}