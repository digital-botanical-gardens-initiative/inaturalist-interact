// main.rs
mod observations;
use observations::get_observation;
// use projects::get_project_info;

#[tokio::main]
async fn main() {
    let observation_id = 195925099;
    match get_observation(observation_id).await {
        Ok(response) => println!("Observation Response: {:?}", response),
        Err(e) => eprintln!("Error: {:?}", e),
    }

    // let project_id = 12345; // Example project ID
    // match get_project_info(project_id).await {
    //     Ok(response) => println!("Project Response: {:?}", response),
    //     Err(e) => eprintln!("Error: {:?}", e),
    // }
}


// config.rs
// Configuration-related functionality
