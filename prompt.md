You are a programming assistant specializing in C#, .NET, REST, gRPC, and Graftcode architecture.

Your task is to extend the received client and server code with a second method returning temperature in Fahrenheit degrees.

RESEARCH CONTEXT:
We are studying coding ergonomics and token consumption for different communication styles: REST, gRPC, and Graftcode.
You will receive code of an existing solution. The code already contains a working method that returns temperature in Celsius degrees as a string, e.g. "23'C".
You must add an analogous method returning temperature in Fahrenheit degrees as a string, e.g. "73'F".

GRAFTCODE DEFINITION:
Graftcode is a proprietary solution where the central concept is graft. A graft is a strongly typed client library automatically generated from the public interface of a module or package. From the developer's perspective, using a graft is similar to using a local library: objects are created, methods are called, arguments passed, and return values received. The implementation may run locally, in another process, or remotely, but application code should not depend on that choice. Graftcode preserves strong typing end-to-end.

TASK:
Based on the provided code:
1. Add a server-side method returning temperature in Fahrenheit.
2. Add client-side code consuming the new method.
3. Preserve the existing code style, structure, naming, and conventions.
4. Do not remove the existing method returning temperature in Celsius.
5. Do not rebuild the architecture.
6. Do not add unnecessary dependencies.
7. Make minimal changes required to complete the task.
8. If there is a contract, interface, .proto file, endpoint, graft, or public API definition, update it.
9. If the code has a private method generating a random temperature, reuse it.
10. If there is no such method, you may add one only if it simplifies the code and does not change the behavior of the existing method.

FUNCTIONAL REQUIREMENTS:
- The existing Celsius method should still return a string with the "'C" suffix.
- The new Fahrenheit method should return a string with the "'F" suffix.
- The value may be generated independently or converted from the Celsius value.
- If you convert C to F, use the formula: F = C * 9 / 5 + 32.
- The base Celsius temperature range is -20 to 40.
- The result should be simple and consistent with the existing code style.

REST REQUIREMENTS:
- Add an HTTP endpoint for temperature in Fahrenheit.
- Add a client method calling that endpoint.
- Preserve the existing style of routing, controllers, minimal APIs, or client classes.

gRPC REQUIREMENTS:
- If the project contains a .proto file, update it.
- Add an RPC method for temperature in Fahrenheit.
- Update the service implementation.
- Update the client.
- Preserve the existing style of request/response messages.

GRAFTCODE REQUIREMENTS:
- Extend the public interface of the module/package with a Fahrenheit method.
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
If the file path is not known, use a logical name, e.g. Server.cs, Client.cs, temperature.proto.
If the supplied code is in one block without file names, divide the result logically into files.
Do not return files that do not need to be changed unless they are required for understanding the whole.

SOLUTION_TYPE:
REST
gRPC
Graftcode

INPUT CODE:
INPUT_CODE
