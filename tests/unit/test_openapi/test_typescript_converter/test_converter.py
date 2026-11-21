import pydantic
from polyfactory import BaseFactory

from litestar import Controller, Litestar, post
from litestar._openapi.typescript_converter.converter import (
    convert_openapi_to_typescript,
)
from litestar.params import JSONBody


def test_openapi_to_typescript_converter(person_controller: type[Controller], pet_controller: type[Controller]) -> None:
    BaseFactory.seed_random(1)
    app = Litestar(route_handlers=[person_controller, pet_controller])
    assert app.openapi_schema

    result = convert_openapi_to_typescript(openapi_schema=app.openapi_schema)
    assert (
        result.write()
        == """export namespace API {
	export namespace PetOwnerOrPetGetPetsOrOwners {
	export namespace Http200 {
	export type ResponseBody = ({
	age: number;
	name: string;
	species?: "Cat" | "Dog" | "Monkey" | "Pig";
} | {
	complex: {
	
};
	first_name: string;
	id: string;
	last_name: string;
	optional: null | string;
	pets?: null | {
	age: number;
	name: string;
	species?: "Cat" | "Dog" | "Monkey" | "Pig";
}[];
})[];

	export interface ResponseHeaders {
	"x-my-tag"?: string;
};
};

	export namespace Http406 {
	export type ResponseBody = {
	detail: string;
	extra?: Record<string, unknown> | null | unknown[];
	status_code: number;
};
};
};

	export namespace PetPets {
	export namespace Http200 {
	export type ResponseBody = {
	age: number;
	name: string;
	species?: "Cat" | "Dog" | "Monkey" | "Pig";
}[];
};
};

	export namespace ServiceIdPersonBulkBulkCreatePerson {
	export interface HeaderParameters {
	secret: string;
};

	export namespace Http201 {
	export type ResponseBody = {
	complex?: {
	
};
	first_name?: string;
	id?: string;
	last_name?: string;
	optional?: null | string;
	pets?: null | {
	age?: number;
	name?: string;
	species?: "Cat" | "Dog" | "Monkey" | "Pig";
}[];
}[];
};

	export namespace Http400 {
	export type ResponseBody = {
	detail: string;
	extra?: Record<string, unknown> | null | unknown[];
	status_code: number;
};
};

	export interface PathParameters {
	service_id: number;
};

	export type RequestBody = {
	complex?: {
	
};
	first_name?: string;
	id?: string;
	last_name?: string;
	optional?: null | string;
	pets?: null | {
	age?: number;
	name?: string;
	species?: "Cat" | "Dog" | "Monkey" | "Pig";
}[];
}[];
};

	export namespace ServiceIdPersonBulkBulkPartialUpdatePerson {
	export interface HeaderParameters {
	secret: string;
};

	export namespace Http200 {
	export type ResponseBody = {
	complex?: {
	
};
	first_name?: string;
	id?: string;
	last_name?: string;
	optional?: null | string;
	pets?: null | {
	age?: number;
	name?: string;
	species?: "Cat" | "Dog" | "Monkey" | "Pig";
}[];
}[];
};

	export namespace Http400 {
	export type ResponseBody = {
	detail: string;
	extra?: Record<string, unknown> | null | unknown[];
	status_code: number;
};
};

	export interface PathParameters {
	service_id: number;
};

	export type RequestBody = {
	complex?: {
	
};
	first_name?: string;
	id?: string;
	last_name?: string;
	optional?: null | string;
	pets?: null | {
	age?: number;
	name?: string;
	species?: "Cat" | "Dog" | "Monkey" | "Pig";
}[];
}[];
};

	export namespace ServiceIdPersonBulkBulkUpdatePerson {
	export interface HeaderParameters {
	secret: string;
};

	export namespace Http200 {
	export type ResponseBody = {
	complex: {
	
};
	first_name: string;
	id: string;
	last_name: string;
	optional: null | string;
	pets?: null | {
	age: number;
	name: string;
	species?: "Cat" | "Dog" | "Monkey" | "Pig";
}[];
}[];
};

	export namespace Http400 {
	export type ResponseBody = {
	detail: string;
	extra?: Record<string, unknown> | null | unknown[];
	status_code: number;
};
};

	export interface PathParameters {
	service_id: number;
};

	export type RequestBody = {
	complex: {
	
};
	first_name: string;
	id: string;
	last_name: string;
	optional: null | string;
	pets?: null | {
	age: number;
	name: string;
	species?: "Cat" | "Dog" | "Monkey" | "Pig";
}[];
}[];
};

	export namespace ServiceIdPersonCreatePerson {
	export interface HeaderParameters {
	secret: string;
};

	export namespace Http201 {
	export type ResponseBody = {
	complex: {
	
};
	first_name: string;
	id: string;
	last_name: string;
	optional: null | string;
	pets?: null | {
	age: number;
	name: string;
	species?: "Cat" | "Dog" | "Monkey" | "Pig";
}[];
};
};

	export namespace Http400 {
	export type ResponseBody = {
	detail: string;
	extra?: Record<string, unknown> | null | unknown[];
	status_code: number;
};
};

	export interface PathParameters {
	service_id: number;
};

	export type RequestBody = {
	complex: {
	
};
	first_name: string;
	id: string;
	last_name: string;
	optional: null | string;
	pets?: null | {
	age: number;
	name: string;
	species?: "Cat" | "Dog" | "Monkey" | "Pig";
}[];
};
};

	export namespace ServiceIdPersonDataclassGetPersonDataclass {
	export namespace Http200 {
	export type ResponseBody = {
	complex: {
	
};
	first_name: string;
	id: string;
	last_name: string;
	optional: null | string;
	pets?: null | {
	age: number;
	name: string;
	species?: "Cat" | "Dog" | "Monkey" | "Pig";
}[];
};
};

	export namespace Http400 {
	export type ResponseBody = {
	detail: string;
	extra?: Record<string, unknown> | null | unknown[];
	status_code: number;
};
};

	export interface PathParameters {
	service_id: number;
};
};

	export namespace ServiceIdPersonGetPersons {
	export interface CookieParameters {
	value: number;
};

	export interface HeaderParameters {
	secret: string;
};

	export namespace Http200 {
	export type ResponseBody = {
	complex: {
	
};
	first_name: string;
	id: string;
	last_name: string;
	optional: null | string;
	pets?: null | {
	age: number;
	name: string;
	species?: "Cat" | "Dog" | "Monkey" | "Pig";
}[];
}[];
};

	export namespace Http400 {
	export type ResponseBody = {
	detail: string;
	extra?: Record<string, unknown> | null | unknown[];
	status_code: number;
};
};

	export interface PathParameters {
	service_id: number;
};

	export interface QueryParameters {
	from_date?: null | number | string | string;
	gender?: "A" | "F" | "M" | "O" | ("A" | "F" | "M" | "O")[] | null;
	lucky_number?: 2 | 7 | null;
	name: null | string | string[];
	page: number;
	pageSize: number;
	to_date?: null | number | string | string;
};
};

	export namespace ServiceIdPersonPersonIdDeletePerson {
	export namespace Http204 {
	export type ResponseBody = undefined;
};

	export namespace Http400 {
	export type ResponseBody = {
	detail: string;
	extra?: Record<string, unknown> | null | unknown[];
	status_code: number;
};
};

	export interface PathParameters {
	person_id: string;
	service_id: number;
};
};

	export namespace ServiceIdPersonPersonIdGetPersonById {
	export namespace Http200 {
	export type ResponseBody = {
	complex: {
	
};
	first_name: string;
	id: string;
	last_name: string;
	optional: null | string;
	pets?: null | {
	age: number;
	name: string;
	species?: "Cat" | "Dog" | "Monkey" | "Pig";
}[];
};
};

	export namespace Http400 {
	export type ResponseBody = {
	detail: string;
	extra?: Record<string, unknown> | null | unknown[];
	status_code: number;
};
};

	export interface PathParameters {
	person_id: string;
	service_id: number;
};
};

	export namespace ServiceIdPersonPersonIdPartialUpdatePerson {
	export namespace Http200 {
	export type ResponseBody = {
	complex?: {
	
};
	first_name?: string;
	id?: string;
	last_name?: string;
	optional?: null | string;
	pets?: null | {
	age?: number;
	name?: string;
	species?: "Cat" | "Dog" | "Monkey" | "Pig";
}[];
};
};

	export namespace Http400 {
	export type ResponseBody = {
	detail: string;
	extra?: Record<string, unknown> | null | unknown[];
	status_code: number;
};
};

	export interface PathParameters {
	person_id: string;
	service_id: number;
};

	export type RequestBody = {
	complex?: {
	
};
	first_name?: string;
	id?: string;
	last_name?: string;
	optional?: null | string;
	pets?: null | {
	age?: number;
	name?: string;
	species?: "Cat" | "Dog" | "Monkey" | "Pig";
}[];
};
};

	export namespace ServiceIdPersonPersonIdUpdatePerson {
	export namespace Http200 {
	export type ResponseBody = {
	complex: {
	
};
	first_name: string;
	id: string;
	last_name: string;
	optional: null | string;
	pets?: null | {
	age: number;
	name: string;
	species?: "Cat" | "Dog" | "Monkey" | "Pig";
}[];
};
};

	export namespace Http400 {
	export type ResponseBody = {
	detail: string;
	extra?: Record<string, unknown> | null | unknown[];
	status_code: number;
};
};

	export interface PathParameters {
	person_id: string;
	service_id: number;
};

	export type RequestBody = {
	complex: {
	
};
	first_name: string;
	id: string;
	last_name: string;
	optional: null | string;
	pets?: null | {
	age: number;
	name: string;
	species?: "Cat" | "Dog" | "Monkey" | "Pig";
}[];
};
};
};"""
    )


class ByNameOrAlias(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(validate_by_name=True)

    user_name: str = pydantic.Field(alias="userName")
    age: int


def test_request_body_accepting_name_or_alias_is_an_interface() -> None:
    @post("/", sync_to_thread=False)
    def handler(data: JSONBody[ByNameOrAlias]) -> None:
        return None

    result = convert_openapi_to_typescript(openapi_schema=Litestar([handler]).openapi_schema)

    assert (
        "export type RequestBody = {\n\tage: number;\n\tuserName?: string;\n\tuser_name?: string;\n};" in result.write()
    )
