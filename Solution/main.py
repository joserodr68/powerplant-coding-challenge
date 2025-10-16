"""
Power Plant Production Planner API

"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
import uvicorn

# DATA MODELS

class Fuels(BaseModel):
    """Fuel costs and wind percentage"""
    gas_euro_mwh: float = Field(..., alias="gas(euro/MWh)")
    kerosine_euro_mwh: float = Field(..., alias="kerosine(euro/MWh)")
    co2_euro_ton: float = Field(..., alias="co2(euro/ton)")
    wind_percent: float = Field(..., alias="wind(%)")

    class Config:
        populate_by_name = True


class PowerPlant(BaseModel):
    """Power plant specifications"""
    name: str
    type: str  # "gasfired", "turbojet", or "windturbine"
    efficiency: float
    pmin: float
    pmax: float


class ProductionPlanRequest(BaseModel):
    """Input payload"""
    load: float
    fuels: Fuels
    powerplants: List[PowerPlant]


class PowerPlantOutput(BaseModel):
    """Output: power produced by each plant"""
    name: str
    p: float

# CALCULATION ALGORITHM

def calculate_cost_per_mwh(plant: PowerPlant, fuels: Fuels) -> float:
    """
    Calculate the cost per MWh for each plant type.
    
    Wind turbines: 0 cost (free energy)
    Gas-fired: (fuel_cost + CO2_cost) / efficiency
               CO2 emission = 0.3 ton per MWh
    Turbojet: kerosine_cost / efficiency
    """
    if plant.type == "windturbine":
        return 0.0
    
    elif plant.type == "gasfired":
        # Fuel cost per MWh of electricity
        fuel_cost = fuels.gas_euro_mwh / plant.efficiency
        # CO2 cost: 0.3 ton CO2 per MWh of electricity
        co2_cost = (0.3 * fuels.co2_euro_ton) / plant.efficiency
        return fuel_cost + co2_cost
    
    elif plant.type == "turbojet":
        return fuels.kerosine_euro_mwh / plant.efficiency
    
    return float('inf')


def calculate_actual_pmax(plant: PowerPlant, fuels: Fuels) -> float:
    """
    Calculate actual maximum power output.
    
    Wind turbines: pmax is reduced by wind percentage
    Other plants: pmax stays the same
    """
    if plant.type == "windturbine":
        return plant.pmax * (fuels.wind_percent / 100.0)
    return plant.pmax


def calculate_production_plan(load: float, fuels: Fuels, powerplants: List[PowerPlant]) -> List[PowerPlantOutput]:
    """
    
    Steps:
    1. Calculate cost per MWh for each plant
    2. Sort plants by cost (cheapest first) = merit order
    3. Activate plants in order until load is met
    4. Handle Pmin constraints carefully
    5. Return production plan rounded to 0.1 MW
    """
    
    # Step 1: Create list of plants with their costs and actual capacity
    plants_data = []
    for plant in powerplants:
        cost = calculate_cost_per_mwh(plant, fuels)
        actual_pmax = calculate_actual_pmax(plant, fuels)
        plants_data.append({
            'plant': plant,
            'cost': cost,
            'actual_pmax': actual_pmax,
            'power': 0.0  # Initially, no power produced
        })
    
    # Step 2: Sort by cost (merit order) - cheapest first
    # If costs are equal, prefer plants with higher capacity
    plants_data.sort(key=lambda x: (x['cost'], -x['actual_pmax']))
    
    # Step 3: Greedy allocation - activate plants in order
    remaining_load = load
    
    for plant_data in plants_data:
        if remaining_load <= 0.1:  # Load satisfied (with 0.1 MW tolerance)
            break
        
        plant = plant_data['plant']
        actual_pmax = plant_data['actual_pmax']
        pmin = plant.pmin
        
        # Skip if plant has no capacity
        if actual_pmax < 0.1:
            continue
        
        # Determine how much power to allocate
        if remaining_load >= pmin:
            # We need at least Pmin, so we can use this plant
            # Produce as much as needed, up to actual_pmax
            power_to_allocate = min(remaining_load, actual_pmax)
            plant_data['power'] = power_to_allocate
            remaining_load -= power_to_allocate
        elif remaining_load > 0 and pmin == 0:
            # Special case: pmin is 0 (wind/turbojet), we can use partial power
            power_to_allocate = min(remaining_load, actual_pmax)
            plant_data['power'] = power_to_allocate
            remaining_load -= power_to_allocate
        elif remaining_load > 0 and actual_pmax >= pmin:
            # We need less than Pmin, but plant must run at Pmin
            # This will cause overproduction, which we'll fix later
            plant_data['power'] = pmin
            remaining_load -= pmin
    
    # Step 4: Handle slight overproduction (negative remaining_load)
    # Try to reduce power from most expensive active plants
    if remaining_load < -0.1:
        for plant_data in reversed(plants_data):  # Start from most expensive
            if plant_data['power'] > 0:
                plant = plant_data['plant']
                excess = abs(remaining_load)
                
                if plant_data['power'] - excess >= plant.pmin:
                    # Reduce power while staying above Pmin
                    plant_data['power'] -= excess
                    remaining_load = 0
                    break
                elif plant.pmin == 0:
                    # Can turn off completely or reduce freely
                    reduction = min(plant_data['power'], excess)
                    plant_data['power'] -= reduction
                    remaining_load += reduction
                    if abs(remaining_load) < 0.1:
                        break
    
    # Step 5: Generate output, round to 0.1 MW
    result = []
    for plant_data in plants_data:
        result.append(PowerPlantOutput(
            name=plant_data['plant'].name,
            p=round(plant_data['power'], 1)
        ))
    
    return result


# FASTAPI APPLICATION


app = FastAPI(
    title="Power Plant Production Planner",
    description="Calculate optimal power production plan",
    version="1.0.0"
)


@app.post("/productionplan", response_model=List[PowerPlantOutput])
async def production_plan(request: ProductionPlanRequest):
    """
    Calculate production plan to meet the load demand.
    
    Returns a list showing how much power (p) each plant should produce.
    The sum of all p values should equal the load.
    """
    try:
        # Calculate the production plan
        plan = calculate_production_plan(
            request.load,
            request.fuels,
            request.powerplants
        )
        
        # Validate: total production should match load
        total_production = sum(plant.p for plant in plan)
        
        if abs(total_production - request.load) > 0.1:
            raise HTTPException(
                status_code=400,
                detail=f"Unable to match load. Load: {request.load} MW, Production: {total_production} MW"
            )
        
        return plan
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        )


@app.get("/")
async def root():
    """API information"""
    return {
        "message": "Power Plant Production Planner API",
        "endpoint": "POST /productionplan",
        "docs": "/docs"
    }




if __name__ == "__main__":
    # Run on port 8888 as required
    uvicorn.run(app, host="0.0.0.0", port=8888)
