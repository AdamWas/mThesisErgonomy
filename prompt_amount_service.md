You are a programming assistant specializing in C#, .NET, REST, gRPC, and Graftcode architecture.

Your task is to create a new amount service based on the received temperature service code.

CONTEXT:
You will receive code of an existing solution. The code contains a working service that returns temperature in Celsius degrees as a string, e.g. "23'C".
Use that code as a structural and stylistic pattern, but create an analogous amount service instead of extending the temperature service.

The received code may not contain any Fahrenheit method. That is expected and does not matter for this task.

GRAFTCODE DEFINITION:
Graftcode is a proprietary solution where the central concept is graft. A graft is a strongly typed client library automatically generated from the public interface of a module or package. From the developer's perspective, using a graft is similar to using a local library: objects are created, methods are called, arguments passed, and return values received. The implementation may run locally, in another process, or remotely, but application code should not depend on that choice. Graftcode preserves strong typing end-to-end.

TASK:
Based on the provided code:
1. Create a server-side amount service with two public methods.
2. Add client-side code consuming both amount methods.
3. Preserve the existing code style, structure, naming, and conventions.
4. Use the provided temperature service only as a pattern for architecture and communication style.
5. Do not rebuild the architecture.
6. Do not add unnecessary dependencies.
7. Make minimal changes required to complete the task.
8. If there is a contract, interface, .proto file, endpoint, graft, or public API definition, update it or create the analogous amount definition.
9. If the code has a private method generating a random value, reuse the style.
10. If there is no such method, you may add one only if it simplifies the code.

FUNCTIONAL REQUIREMENTS:
- Create a method returning a random decimal amount in PLN.
- Create a method returning a random decimal amount multiplied by 3.65 in USD.
- The random base amount range is 0 to 1000.
- Business correctness of currency conversion is not important. Treat this as a thin mock facade.
- All returned values must be strings.
- The PLN method should return a string formatted like "123.05 PLN".
- The USD method should return a string formatted like "65.40 USD".
- Both methods must always return exactly two decimal places.
- The result should be simple and consistent with the existing code style.

REST REQUIREMENTS:
- Create an HTTP endpoint returning the amount in PLN.
- Create an HTTP endpoint returning the amount in USD.
- Recommended endpoint names are:
  - /amount/pln
  - /amount/usd
- Add client code calling both endpoints.
- Preserve the existing style of routing, controllers, minimal APIs, or client classes.

gRPC REQUIREMENTS:
- If the project contains a .proto file, update it or create the analogous amount service definition.
- Add an RPC method returning the amount in PLN.
- Add an RPC method returning the amount in USD.
- Recommended RPC method names are:
  - GetAmountPln
  - GetAmountUsd
- Update the service implementation.
- Update the client.
- Preserve the existing style of request/response messages.
- Return the amount as a string field, consistent with the input code style.

GRAFTCODE REQUIREMENTS:
- Create or extend the public interface of the module/package with amount methods.
- Recommended method names are:
  - GetAmountPln()
  - GetAmountUsd()
- Update the server/module implementation.
- Update the graft-using client code.
- Preserve the graft usage style as a local, strongly typed library.
- Do not introduce manual transport logic in client code if the existing Graftcode style does not do so.

RESPONSE FORMAT:
Return the complete ready code, divided into files.
Do not return a unified diff.
Do not omit any changed file.
Do not add long explanations.
Use exactly this format:

=== FILE: path/to/file.ext ===
language
full file contents
=== FILE: path/to/next/file.ext ===
If the file path is not known, use a logical name, e.g. Server.cs, Client.cs, amount.proto.
If the supplied code is in one block without file names, divide the result logically into files.
Do not return files that do not need to be changed unless they are required for understanding the whole.

SOLUTION_TYPE:
REST
gRPC
Graftcode

INPUT CODE:
INPUT_CODE
