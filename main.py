from twisted.internet import reactor
import bot

factory = bot.BotClientFactory("#thasaucetest")
reactor.connectTCP("irc.esper.net", 6667, factory, 300)
reactor.run()