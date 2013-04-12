from twisted.internet import reactor
import bot

factory = bot.PartyBotFactory("#thasauce")
reactor.connectTCP("irc.esper.net", 6667, factory)
reactor.run()