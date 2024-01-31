use inaturalist::apis::observations_api::observations_id_get;
use inaturalist::apis::configuration;
use inaturalist::apis::observations_api::ObservationsIdGetParams;

#[tokio::main]
async fn main() {
    let mut config = configuration::Configuration::default();
    
    // Set the base URL for the API
    config.base_path = "https://api.inaturalist.org/v1".to_string();

    let observation_id = ObservationsIdGetParams {
        id: vec![195925099],
    };

    match observations_id_get(&config, observation_id).await {
        Ok(response) => println!("Response: {:?}", response),
        Err(e) => eprintln!("Error: {:?}", e),
    }
}
