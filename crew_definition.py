from crewai import Agent, Crew, Task
from logging_config import get_logger

class AIEducationCrew:
    def __init__(self, verbose=True, logger=None):
        self.verbose = verbose
        self.logger = logger or get_logger(__name__)
        self.crew = self.create_crew()
        self.logger.info("AIEducationCrew initialized")

    def create_crew(self):
        self.logger.info("Creating versatile AI assistant crew")
        
        researcher = Agent(
            role='Knowledge Specialist',
            goal='Provide accurate information on any topic, with special expertise in AI, machine learning, and technology',
            backstory='Versatile researcher with broad knowledge across many topics. Excels at finding accurate, helpful information whether it\'s about AI, technology, science, or general knowledge. When AI topics are mentioned, provides expert-level insights on machine learning, neural networks, NLP, computer vision, and AI ethics.',
            verbose=self.verbose
        )

        responder = Agent(
            role='Helpful Assistant',
            goal='Create clear, concise responses under 200 characters that help users understand any topic',
            backstory='Friendly, knowledgeable assistant who can discuss anything from everyday questions to complex technical topics. Specializes in AI and technology but equally comfortable helping with general questions. Always provides accurate, helpful information in a clear, engaging way.',
            verbose=self.verbose
        )

        self.logger.info("Created versatile assistant agents")

        crew = Crew(
            agents=[researcher, responder],
            tasks=[
                Task(
                    description='Research and understand: {text}. If it\'s AI-related, provide expert technical insights. For general topics, provide clear, helpful information.',
                    expected_output='Accurate, detailed information about the topic, with special depth for AI/tech questions',
                    agent=researcher
                ),
                Task(
                    description='Create helpful response',
                    expected_output='Clear, accurate response under 200 characters. For AI topics: be educational and precise. For general topics: be helpful and friendly. Always be informative and engaging.',
                    agent=responder
                )
            ]
        )
        self.logger.info("Versatile AI assistant crew setup completed")
        return crew