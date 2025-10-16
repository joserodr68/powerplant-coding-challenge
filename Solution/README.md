# Power Plant Production Planner API

A REST API that calculates the optimal power production plan for a fleet of powerplants to meet electricity demand. The API uses a custom algorithm to minimize production costs while respecting operational constraints.



---

## Challenge Requirements

This implementation meets all the acceptance criteria:

✅ **REST API** with `/productionplan` endpoint  
✅ **Accepts POST** requests with payload structure as specified  
✅ **Returns JSON** response with power output for each plant  
✅ **Custom algorithm**  
✅ **Python 3.8+** implementation  
✅ **requirements.txt** included for dependencies  
✅ **README.md** with build and launch instructions  
✅ **Exposes API on port 8888**   
✅ **Dockerfile** included for easy deployment  


---

## Algorithm Explanation


The algorithm solves the **unit commitment problem** by dispatching powerplants in order of their cost per MWh (merit order), from cheapest to most expensive.

### Steps:

#### **1. Calculate Cost per MWh**

For each powerplant, calculate the production cost:

- **Wind Turbines**: 
  ```
  Cost = 0 €/MWh (free energy)
  ```

- **Gas-fired Plants**: 
  ```
  Cost = (fuel_cost / efficiency) + (CO2_emission_cost / efficiency)
  where CO2_emission = 0.3 ton per MWh
  ```

- **Turbojets**: 
  ```
  Cost = kerosine_cost / efficiency
  ```

#### **2. Adjust for Wind Percentage**

Wind turbines can only produce based on available wind:
```
Actual Power = pmax × (wind% / 100)
```

#### **3. Sort **

Sort all powerplants by cost (lowest to highest). This creates the **merit order**.

#### **4.  Allocation**

Activate plants in order:
- Start with the cheapest plant
- Allocate as much power as needed (up to pmax)
- Move to next plant if more power is needed
- Respect **Pmin constraint**: if a plant is activated, it must produce at least Pmin
- Continue until total production = load

#### **5. Handle Overproduction**

If Pmin constraints cause overproduction:
- Reduce output from most expensive active plants
- Ensure plants still meet their Pmin requirements
- Turn off plants completely if needed (only if Pmin = 0)

#### **6. Round Output**

Round all power outputs to **0.1 MW precision**.

---

## Installation

### Prerequisites

- **Python 3.8 or higher**
- **pip** (Python package manager)

OR

- **Docker** (for containerized deployment)

### Install Dependencies

```bash
pip install -r requirements.txt
```

The required dependencies are:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pydantic` - Data validation

---

## Running the Application

### Option 1: Run Directly with Python

```bash
python main.py
```

The API will start on **http://localhost:8888**



### Option 2: Run with Docker

#### Build the Docker image:
```bash
docker build -t powerplant-api .
```

#### Run the container:
```bash
docker run -p 8888:8888 powerplant-api
```

The API will be available at **http://localhost:8888**

---

## API Usage

### Endpoints

- **POST /productionplan** - Calculate production plan
- **GET /** - API information
- **GET /docs** - Interactive API documentation (Swagger UI)
- **GET /redoc** - Alternative API documentation


