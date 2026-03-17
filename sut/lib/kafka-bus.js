const { EventEmitter } = require('events');

function createKafkaBus() {
  const emitter = new EventEmitter();

  function publish(topic, event) {
    emitter.emit(topic, event);
  }

  function subscribe(topic, handler) {
    emitter.on(topic, handler);
    return () => emitter.off(topic, handler);
  }

  return {
    publish,
    subscribe,
  };
}

module.exports = { createKafkaBus };

