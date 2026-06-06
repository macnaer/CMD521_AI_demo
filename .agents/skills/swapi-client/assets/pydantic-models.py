"""Pydantic models for SWAPI data validation and processing."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SWAPIBase(BaseModel):
    url: str
    created: str = ""
    edited: str = ""


class Person(SWAPIBase):
    name: str
    height: str = "0"
    mass: str = "0"
    hair_color: str = ""
    skin_color: str = ""
    eye_color: str = ""
    birth_year: str = ""
    gender: str = ""
    homeworld: str = ""
    films: list[str] = []
    species: list[str] = []
    vehicles: list[str] = []
    starships: list[str] = []


class Film(SWAPIBase):
    title: str
    episode_id: int
    opening_crawl: str = ""
    director: str = ""
    producer: str = ""
    release_date: str = ""
    characters: list[str] = []
    planets: list[str] = []
    starships: list[str] = []
    vehicles: list[str] = []
    species: list[str] = []


class Planet(SWAPIBase):
    name: str
    rotation_period: str = "0"
    orbital_period: str = "0"
    diameter: str = "0"
    climate: str = ""
    gravity: str = ""
    terrain: str = ""
    surface_water: str = "0"
    population: str = "0"
    residents: list[str] = []
    films: list[str] = []


class Species(SWAPIBase):
    name: str
    classification: str = ""
    designation: str = ""
    average_height: str = "0"
    skin_colors: str = ""
    hair_colors: str = ""
    eye_colors: str = ""
    average_lifespan: str = "0"
    homeworld: str | None = None
    language: str = ""
    people: list[str] = []
    films: list[str] = []


class Vehicle(SWAPIBase):
    name: str
    model: str = ""
    manufacturer: str = ""
    cost_in_credits: str = "0"
    length: str = "0"
    max_atmosphering_speed: str = "0"
    crew: str = "0"
    passengers: str = "0"
    cargo_capacity: str = "0"
    consumables: str = ""
    vehicle_class: str = ""
    pilots: list[str] = []
    films: list[str] = []


class Starship(SWAPIBase):
    name: str
    model: str = ""
    manufacturer: str = ""
    cost_in_credits: str = "0"
    length: str = "0"
    max_atmosphering_speed: str = "0"
    crew: str = "0"
    passengers: str = "0"
    cargo_capacity: str = "0"
    consumables: str = ""
    hyperdrive_rating: str = "0"
    MGLT: str = "0"
    starship_class: str = ""
    pilots: list[str] = []
    films: list[str] = []
