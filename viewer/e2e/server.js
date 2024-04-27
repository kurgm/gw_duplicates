// @ts-check

const path = require("node:path");
const Fastify = require("fastify");
const fastifyStatic = require("@fastify/static");

const resultJson = require("./test-result.json");

/**
 * @param {string} text
 * @returns {string}
 */
const encodeHTML = (text) =>
  text.replace(/[&<>"']/g, (match) => `&#${match.charCodeAt(0)};`);

const fastify = Fastify({ logger: true });

fastify.register(fastifyStatic, {
  root: path.join(__dirname, "../dist"),
  prefix: "/viewer/",
});

fastify.get("/result.json", (_request, reply) => {
  reply.send(resultJson);
});

fastify.get("/wiki/:name", (request, reply) => {
  /** @type {{ name: string }} */
  const { name } = /** @type {any} */ (request.params);
  /** @type {Record<string, string | string[] | undefined>} */
  const { action, related, summary, textbox } = /** @type {any} */ (
    request.query
  );

  if (!/^[a-z0-9_@-]+$/.test(name)) {
    reply.code(400).send("Invalid name");
    return;
  }

  /**
   * @param {string} label
   * @param {unknown} value
   * @returns {string}
   */
  const printTextArea = (label, value) =>
    typeof value === "string" && value.length > 0
      ? `
        <div>
          <label>
            ${encodeHTML(label)}
            <textarea>${encodeHTML(value)}</textarea>
          </label>
        </div>`
      : "";

  reply.type("text/html").send(
    `
      <!DOCTYPE html>
      <title>${action === "preview" ? "Editing " : ""}${name}</title>
      <h1>${name}</h1>
      ${printTextArea("related", related)}
      ${printTextArea("summary", summary)}
      ${printTextArea("textbox", textbox)}
    `.trim()
  );
});

fastify.get("/glyph/:name.svg", (request, reply) => {
  /** @type {{ name: string }} */
  const { name } = /** @type {any} */ (request.params);

  if (!/^[a-z0-9_@-]+$/.test(name)) {
    reply.code(400).send("Invalid name");
    return;
  }

  reply.type("image/svg+xml").send(
    `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
      </svg>
    `.trim()
  );
});

fastify.listen({ port: +(process.env.PORT || 3000) }, (err, address) => {
  if (err) {
    fastify.log.error(err);
    process.exit(1);
  }
  fastify.log.info(`server listening on ${address}`);
});
