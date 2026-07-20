<a id="readme-top"></a>

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]

<br />
<div align="center">

  <h3 align="center">AI-Based Intrusion Detection System for IoT Traffic</h3>

  <p align="center">
    End-to-end IoT intrusion detection pipeline that captures traffic, extracts CIC-style flow features, classifies streams with a Spark ML Random Forest model, and stores alerts in PostgreSQL.
    <br />
    <a href="docs/GITHUB_DESCRIPTION.md"><strong>Explore the docs</strong></a>
    <br />
    <br />
    <a href="#usage">View Usage</a>
    &middot;
    <a href="https://github.com/ahmed3bahaa/AI-Based-IDS-/issues/new">Report Bug</a>
    &middot;
    <a href="https://github.com/ahmed3bahaa/AI-Based-IDS-/issues/new">Request Feature</a>
  </p>
</div>

<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-project">About The Project</a><ul><li><a href="#built-with">Built With</a></li></ul></li>
    <li><a href="#getting-started">Getting Started</a><ul><li><a href="#prerequisites">Prerequisites</a></li><li><a href="#installation">Installation</a></li></ul></li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#how-it-works">How It Works</a></li>
    <li><a href="#project-structure">Project Structure</a></li>
    <li><a href="#validation">Validation</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

## About The Project

<p align="center">
  <img src="docs/images/ConfusionMatrix.png" alt="Confusion matrix" width="86%">
</p>

End-to-end IoT intrusion detection pipeline that captures traffic, extracts CIC-style flow features, classifies streams with a Spark ML Random Forest model, and stores alerts in PostgreSQL.

The repository currently offers:

- Mininet topology with attack hosts and NAT uplink
- HTTP, TCP, and MQTT traffic generation toward IoT targets
- Packet capture with dumpcap
- PCAP to CIC-style CSV conversion
- Spark Structured Streaming classifier
- Saved RF-20 Random Forest model
- PostgreSQL alert storage and SQL initialization


<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

- Python
- Apache Spark
- PostgreSQL
- Docker Compose
- Mininet
- CICFlowMeter
- Bash

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Getting Started

Follow these steps to clone the repository and run the project locally.

### Prerequisites

- Linux or Ubuntu lab environment
- Python and pip
- Docker Compose for database services
- Mininet and capture tools for live lab use

### Installation

~~~bash
git clone https://github.com/ahmed3bahaa/AI-Based-IDS-.git
cd AI-Based-IDS-
cp .env.example .env
pip install -r requirements.txt
docker compose up -d
~~~

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Usage

Useful commands and entry points:

~~~bash
bash run_live_detection.sh
~~~

~~~bash
bash capture.sh
~~~

~~~bash
python ids_streaming.py
~~~

~~~bash
python mininet_attack.py
~~~

### Model Evaluation

These charts show the current model evaluation artifacts saved with the project. They make the Random Forest results visible before anyone has to rerun the whole live capture and Spark pipeline.

<p align="center">
  <img src="docs/images/ConfusionMatrix.png" alt="Confusion matrix" width="48%">
  <img src="docs/images/F1.png" alt="F1 score chart" width="48%">
</p>

<p align="center">
  <img src="docs/images/FalsePositive.png" alt="False positive chart" width="48%">
  <img src="docs/images/Persecion.png" alt="Precision chart" width="48%">
</p>

<p align="center">
  <img src="docs/images/Recall.png" alt="Recall chart" width="48%">
</p>

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## How It Works

```text
Mininet or LAN traffic -> packet capture -> PCAP to CSV -> Spark model RF-20 -> prediction label -> PostgreSQL IDS alerts
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Project Structure

- ids_streaming.py - streaming detection pipeline
- mininet_attack.py - attack traffic lab script
- capture.sh and pcap_to_csv.sh - packet capture and feature extraction helpers
- sql/ - database initialization
- RF-20/ - saved Spark ML model artifacts
- docs/ - architecture and deployment guides

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Validation

Run the most relevant checks for this repository:

~~~bash
python -m py_compile ids_streaming.py mininet_attack.py gen_schema.py
~~~

~~~bash
docker compose config
~~~

Live checks need the matching local services, datasets, credentials, or lab tools installed first.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Roadmap

- Add more labelled IoT traffic scenarios so the model can be compared across normal, scan, TCP, HTTP, and MQTT behavior.
- Document the dataset preparation steps in more detail, especially the columns expected by the Spark streaming job.
- Add a small dashboard or report export for reviewing stored alerts from PostgreSQL.
- Keep the Mininet lab scripts aligned with the Docker and database setup.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Contributing

Contributions are welcome for documentation, examples, tests, and implementation improvements.

1. Fork the project.
2. Create your feature branch:

   ~~~bash
   git checkout -b feature/AmazingFeature
   ~~~

3. Commit your changes:

   ~~~bash
   git commit -m "Add some AmazingFeature"
   ~~~

4. Push to the branch:

   ~~~bash
   git push origin feature/AmazingFeature
   ~~~

5. Open a pull request.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Top Contributors

<a href="https://github.com/ahmed3bahaa/AI-Based-IDS-/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=ahmed3bahaa/AI-Based-IDS-" alt="Top contributors for AI-Based Intrusion Detection System for IoT Traffic" />
</a>

## License

This repository does not include a root license yet. Add one before reusing or distributing the project outside its original coursework, lab, or prototype context.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Contact

Project owner: [@ahmed3bahaa](https://github.com/ahmed3bahaa)

Project Link: [https://github.com/ahmed3bahaa/AI-Based-IDS-](https://github.com/ahmed3bahaa/AI-Based-IDS-)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Acknowledgments

- README structure adapted from [ahmed3bahaa/readme-template](https://github.com/ahmed3bahaa/readme-template).
- Project files, reports, fixtures, and documentation included in this repository.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

[contributors-shield]: https://img.shields.io/github/contributors/ahmed3bahaa/AI-Based-IDS-.svg?style=for-the-badge
[contributors-url]: https://github.com/ahmed3bahaa/AI-Based-IDS-/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/ahmed3bahaa/AI-Based-IDS-.svg?style=for-the-badge
[forks-url]: https://github.com/ahmed3bahaa/AI-Based-IDS-/network/members
[stars-shield]: https://img.shields.io/github/stars/ahmed3bahaa/AI-Based-IDS-.svg?style=for-the-badge
[stars-url]: https://github.com/ahmed3bahaa/AI-Based-IDS-/stargazers
[issues-shield]: https://img.shields.io/github/issues/ahmed3bahaa/AI-Based-IDS-.svg?style=for-the-badge
[issues-url]: https://github.com/ahmed3bahaa/AI-Based-IDS-/issues
