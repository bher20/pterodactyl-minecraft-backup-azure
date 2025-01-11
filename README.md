# Pterodactyl Minecraft Backup to Azure

This project provides a solution to back up your Minecraft server data from Pterodactyl to Azure Blob Storage.

## Prerequisites

- Pterodactyl Panel
- Azure Storage Account
- Azure CLI

## Installation

1. Clone the repository:
  ```sh
  git clone https://github.com/yourusername/pterodactyl-minecraft-backup-azure.git
  cd pterodactyl-minecraft-backup-azure
  ```

2. Configure Azure CLI and login:
  ```sh
  az login
  ```

3. Set up your Azure Storage Account and container:
  ```sh
  az storage account create --name <your_storage_account_name> --resource-group <your_resource_group> --location <your_location>
  az storage container create --name <your_container_name> --account-name <your_storage_account_name>
  ```

## Usage

1. Run the backup script:
  ```sh
  docker run \
  -e "AZURE_STORAGE_CONTAINER=test" \
  -e "AZURE_STORAGE_BLOB_PREFIX=minecraft-01" \
  -e "AZURE_STORAGE_CONTAINER=test" \
  -e "AZURE_STORAGE_CONNECTION_STRING=test" \
  -e "AZURE_STORAGE_SAS_TOKEN=test" \
  -v /path/to/backups:/backups pterodactyl-minecraft-backup-azure:latest
  ```

2. Schedule the script using a cron job or Pterodactyl's scheduled tasks.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For any questions or support, please open an issue on the GitHub repository.
