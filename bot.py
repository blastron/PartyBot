from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, task
import stream
from compo import Compo
from datetime import datetime
import traceback


class PartyBot:
    def __init__(self):
        self.irc_client = None

        self.streamer = stream.ShoutcastStreamer()
        self.streamer.start()

        self.compo = None

        self.scheduled_compo_id = None
        self.scheduled_compo_start = None

    def handle_message(self, user, is_private, message):
        if not user:
            return

        if is_private or message[0] == "!":
            # Command has been received, either through a private message or as a !command in IRC.
            if message[0] == "!":
                # If the command starts with !, remove the !.
                message = message[1:]

            split_message = message.split(' ')
            command = split_message[0].lower()
            arguments = split_message[1:]

            if command == "party":
                self.party(arguments, user, is_private)
            elif command == "schedule":
                self.schedule(arguments, user, is_private)
            elif command == "stop":
                self.stop_party(arguments, user, is_private)
            elif command == "skip":
                self.vote_skip(arguments, user, is_private)
            elif command == "noskip":
                self.vote_noskip(arguments, user, is_private)
            elif command == "say":
                if is_private and user == "blastron":
                    self.irc_client.broadcast(" ".join(arguments))
                else:
                    self.irc_client.broadcast_response(user, "Don't try to put words in my mouth.", is_private)
            elif command == "help":
                self.display_help(arguments, user, is_private)
            else:
                self.irc_client.broadcast_response(
                    user, "Unrecognized command \"%s\". Type !help for available commands." % command, is_private)

    def tick(self):
        if self.compo:
            self.compo.update()
            if self.compo.state in (Compo.State.Complete, Compo.State.Error):
                self.compo = None
        elif self.scheduled_compo_start and self.scheduled_compo_start < datetime.utcnow():
            self.start_scheduled_party()
            self.scheduled_compo_id = None
            self.scheduled_compo_start = None

    def party(self, arguments, user, is_private):
        if len(arguments) in (1, 2):
            if not self.compo:
                self.broadcast_stream_url()
                compo_id = arguments[0]

                start_index = 0
                if len(arguments) == 2 and arguments[1].isdigit():
                    start_index = int(arguments[1])

                self.compo = Compo(compo_id, self, self.streamer)
                self.compo.start(start_index)
            else:
                self.irc_client.broadcast_response(
                    user, "A party is already happening. Use !stop to cancel it.", is_private)
        else:
            self.display_help(["party"], user, is_private)

    def schedule(self, arguments, user, is_private):
        if len(arguments) == 3:
            self.scheduled_compo_id = arguments[0]
            self.scheduled_compo_start = datetime.strptime("%s %s" % (arguments[1], arguments[2]), "%m/%d/%Y %H:%M")
            self.irc_client.broadcast_response(user, "Party has been scheduled.", is_private)
        else:
            self.display_help(["schedule"], user, is_private)

    def start_scheduled_party(self):
        self.irc_client.broadcast("Starting scheduled party...")
        self.broadcast_stream_url()
        self.compo = Compo(self.scheduled_compo_id, self, self.streamer)
        self.compo.start()

    def stop_party(self, arguments, user, is_private):
        if self.compo:
            self.compo = None
            self.streamer.Stop()
            self.irc_client.broadcast("Stopping party...")
        else:
            self.irc_client.broadcast_response(user, "No party is currently happening.", is_private)

    def vote_skip(self, arguments, user, is_private):
        pass

    def vote_noskip(self, arguments, user, is_private):
        pass

    commands = {
        "party": "Starts a new party immediately. Usage: \x0306!party compo_id\x0F.",
        "schedule": "Schedules a party for the future. Usage: \x0306!schedule compo_id MM/DD/YYYY HH:MM\x0F. " +
                    "Time is in 24-hour UTC.",
        "stop": "Stops the current party.",
        # "skip": "Starts a vote for the current song to be skipped.",
    }

    def display_help(self, arguments, user, is_private):
        if len(arguments) == 1 and arguments[0] in self.commands:
            self.irc_client.broadcast_response(user, "!%s - %s" % (arguments[0], self.commands[arguments[0]]),
                                               is_private)
        else:
            self.irc_client.broadcast_response(user, ", ".join(self.commands.keys()), is_private)

    def broadcast_stream_url(self):
        self.irc_client.broadcast("*** Jukebox is online. Tune in at http://blastron.us.to:8000/partybot.m3u ***")


bot_instance = PartyBot()


class BotClient(irc.IRCClient):
    nickname = "partybot"

    def __init__(self):
        self.is_joined = False
        bot_instance.irc_client = self

        self.ticker = task.LoopingCall(self.handle_tick)

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        print "Connection established."

        self.start_ticker()

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        print "Connection lost."

        self.stop_ticker()

    # callbacks for events
    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)
        self.broadcast("Partybot online.")

    def joined(self, channel):
        """This will get called when the bot joins the channel.
        :param channel: The channel that was just joined.
        """
        print "Channel %s joined." % channel
        self.is_joined = True

    def privmsg(self, user, channel, message):
        """This will get called when the bot receives a message.
        :param user: The user who sent the message
        :param channel: The channel where the message was sent
        :param message: The message
        """
        user = user.split('!', 1)[0]
        is_private = channel == self.nickname

        bot_instance.handle_message(user, is_private, message)

    def start_ticker(self):
        self.ticker.start(0.1)

    def stop_ticker(self):
        self.ticker.stop()

    def handle_tick(self):
        if self.is_joined:
            try:
                bot_instance.tick()
            except Exception:
                traceback.print_exc()

    # IRC interactions
    def broadcast(self, text):
        self.broadcast_private(self.factory.channel, text)

    def broadcast_private(self, recipient, text):
        print "Broadcasting to %s: %s" % (recipient, text)
        self.msg(recipient, ''.join(['\x02', text]).encode("utf-8"))

    def broadcast_response(self, recipient, text, is_private):
        if is_private:
            self.broadcast_private(recipient, text)
        else:
            self.broadcast(recipient + ": " + text)


class BotClientFactory(protocol.ReconnectingClientFactory):
    def __init__(self, channel):
        self.channel = channel
        
        self.maxDelay = 300
        self.initialDelay = 5
        self.factor = 2

    def buildProtocol(self, addr):
        p = BotClient()
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        print "Connection to server lost: ", reason
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        print "Connection to server failed: ", reason
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
