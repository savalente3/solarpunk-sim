"""The shapes of the agents' answers: what the allotment manager says, what the
building manager decides, and what the shop gives.

Every model must answer in exactly these shapes, so every answer can be read and
carried out the same way. Lists rather than maps, because every provider's
structured output handles a list of small objects.
"""
from typing import Literal

from pydantic import BaseModel, Field

from settlement.allotment import Allotment

Crop = Literal[Allotment.crops]


class PerDay(BaseModel):
    water_per_day: float = Field(ge=0, description="litres of fresh rainwater a day")
    greywater_per_day: float = Field(ge=0, description="litres of greywater a day")
    energy_per_day: float = Field(ge=0, description="kWh a day")


class Planting(BaseModel):
    crop: Crop
    beds: int = Field(ge=0, description="how many empty beds to plant with it")


class Move(BaseModel):
    crop: Crop
    kg: float = Field(ge=0)


class AllotmentAnswer(BaseModel):
    """What the allotment manager tells the building manager."""

    beds_need: PerDay = Field(description="what the beds need each day until the next decision")
    plant: list[Planting] = Field(description="what to plant in empty beds; empty if nothing")
    message: str = Field(description="a short message to the building manager")


class Tenants(BaseModel):
    energy: float = Field(ge=0, le=1, description="share of their normal energy need they may use: 1 all of it, 0 none even if the battery is full")
    water: float = Field(ge=0, le=1, description="share of their normal water need they may use: 1 all of it, 0 none even if the tank is full")
    food: float = Field(ge=0, le=1, description="share of their normal food need they may eat: 1 all of it, 0 none even if food storage is full")


class Now(BaseModel):
    move_to_food_storage: list[Move] = Field(description="produce to move from the allotment's store into food storage")
    plant: list[Planting] = Field(description="what to plant in empty beds")


class UntilNextTime(BaseModel):
    tenants: Tenants
    beds: PerDay = Field(description="what the beds get each day")


class ShopRequest(BaseModel):
    send_surplus: list[Move] = Field(description="produce to send from the allotment's store to the shop; empty for none")
    water_wanted: float = Field(ge=0, description="litres of water to ask the shop for; 0 for none")
    produce_wanted: list[Move] = Field(description="produce to ask the shop for; empty for none")
    message: str = Field(description="a short note to the shop; empty if nothing")


class BuildingDecision(BaseModel):
    """What the building manager decides."""

    reasoning: str = Field(description="one or two sentences: why this decision")
    now: Now
    until_next_time: UntilNextTime
    shop: ShopRequest = Field(description="what to send the shop and ask of it; all empty if nothing")
    check_again_in_days: int = Field(ge=1, le=3, description="when to be checked on again, in days")


class ShopAnswer(BaseModel):
    """What the shop gives a building that has asked it for something."""

    reasoning: str = Field(description="one or two sentences: why")
    water_given: float = Field(ge=0, description="litres of water to give the building now; 0 for none")
    produce_given: list[Move] = Field(description="produce to give the building now; empty for none")
    suggest_planting: list[Move] = Field(description="what that building should grow next, as crop and kg, for the settlement's variety; empty for no suggestion")
    message: str = Field(description="a short message to that building's managers")
