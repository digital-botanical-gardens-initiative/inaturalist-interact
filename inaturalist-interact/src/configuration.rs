use inaturalist::apis::configuration::BasicAuth;
use inaturalist::apis::configuration::Client;
use inaturalist::apis::configuration::ApiKey;

pub struct Configuration {
    pub base_path: String,
    pub user_agent: Option<String>,
    pub client: Client,
    pub basic_auth: Option<BasicAuth>,
    pub oauth_access_token: Option<String>,
    pub bearer_access_token: Option<String>,
    pub api_key: Option<ApiKey>,
}

impl Configuration {
    pub fn new() -> Configuration {
        // Initialize the logger here.
        init_logger();
        
        Configuration {
            base_path: String::from("YOUR_BASE_PATH"),
            user_agent: Some(String::from("YOUR_USER_AGENT")),
            client: Client::default(),
            basic_auth: None,
            oauth_access_token: None,
            bearer_access_token: None,
            api_key: None,
        }
    }
}

