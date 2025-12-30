from langgraph.graph import StateGraph,START, END
from src.dev_pilot.state.sdlc_state import SDLCState
from src.dev_pilot.nodes.project_requirement_node import ProjectRequirementNode
from src.dev_pilot.nodes.design_document_node import DesingDocumentNode
from src.dev_pilot.nodes.coding_node import CodingNode
from src.dev_pilot.nodes.markdown_node import MarkdownArtifactsNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables.graph import MermaidDrawMethod

class GraphBuilder:
    
    def __init__(self, llm):
        self.llm = llm
        self.graph_builder = StateGraph(SDLCState)
        self.memory = MemorySaver()
                
    
    def build_sdlc_graph(self):
        """
            Configure the graph by adding nodes, edges
        """
        
        self.project_requirement_node = ProjectRequirementNode(self.llm)
        self.design_document_node = DesingDocumentNode(self.llm)
        self.coding_node = CodingNode(self.llm)
        self.markdown_node = MarkdownArtifactsNode()
        
        ## Nodes
        self.graph_builder.add_node("initialize_project", self.project_requirement_node.initialize_project)
        self.graph_builder.add_node("get_user_requirements", self.project_requirement_node.get_user_requirements)
        
        self.graph_builder.add_node("generate_user_stories", self.project_requirement_node.generate_user_stories)
        self.graph_builder.add_node("review_user_stories", self.project_requirement_node.review_user_stories)
        self.graph_builder.add_node("revise_user_stories", self.project_requirement_node.revise_user_stories)
        
        self.graph_builder.add_node("create_design_documents", self.design_document_node.create_design_documents)
        self.graph_builder.add_node("review_design_documents", self.design_document_node.review_design_documents)
        self.graph_builder.add_node("revise_design_documents", self.design_document_node.revise_design_documents)
        
        self.graph_builder.add_node("generate_code", self.coding_node.generate_code)
        self.graph_builder.add_node("code_review", self.coding_node.code_review)
        self.graph_builder.add_node("fix_code", self.coding_node.fix_code)
        
        self.graph_builder.add_node("security_review_recommendations", self.coding_node.security_review_recommendations)
        self.graph_builder.add_node("security_review", self.coding_node.security_review)
        self.graph_builder.add_node("fix_code_after_security_review", self.coding_node.fix_code_after_security_review)
       
        self.graph_builder.add_node("write_test_cases", self.coding_node.write_test_cases)
        self.graph_builder.add_node("review_test_cases", self.coding_node.review_test_cases)
        self.graph_builder.add_node("revise_test_cases", self.coding_node.revise_test_cases)
        
        self.graph_builder.add_node("qa_testing", self.coding_node.qa_testing)
        self.graph_builder.add_node("qa_review", self.coding_node.qa_review)
        self.graph_builder.add_node("deployment", self.coding_node.deployment)
        self.graph_builder.add_node("donwload_artifacts", self.markdown_node.generate_markdown_artifacts)
        
        
        ## Edges
        self.graph_builder.add_edge(START,"initialize_project")
        self.graph_builder.add_edge("initialize_project","get_user_requirements")
        self.graph_builder.add_edge("get_user_requirements","generate_user_stories")
        self.graph_builder.add_edge("generate_user_stories","review_user_stories") 
        self.graph_builder.add_conditional_edges(
            "review_user_stories",
            self.project_requirement_node.review_user_stories_router,
            {
                "approved": "create_design_documents",
                "feedback": "revise_user_stories"
            }
        )
        self.graph_builder.add_edge("revise_user_stories","generate_user_stories")
        self.graph_builder.add_edge("create_design_documents","review_design_documents")
        self.graph_builder.add_conditional_edges(
            "review_design_documents",
            self.design_document_node.review_design_documents_router,
            {
                "approved": "generate_code",
                "feedback": "revise_design_documents"
            }
        )
        self.graph_builder.add_edge("revise_design_documents","create_design_documents")
        self.graph_builder.add_edge("generate_code","code_review")
        self.graph_builder.add_conditional_edges(
            "code_review",
            self.coding_node.code_review_router,
            {
                "approved": "security_review_recommendations",
                "feedback": "fix_code"
            }
        )
        self.graph_builder.add_edge("fix_code","generate_code")
        self.graph_builder.add_edge("security_review_recommendations","security_review")
        self.graph_builder.add_conditional_edges(
            "security_review",
            self.coding_node.security_review_router,
            {
                "approved": "write_test_cases",
                "feedback": "fix_code_after_security_review"
            }
        )
        self.graph_builder.add_edge("fix_code_after_security_review","generate_code")
        self.graph_builder.add_edge("write_test_cases", "review_test_cases")
        self.graph_builder.add_conditional_edges(
            "review_test_cases",
            self.coding_node.review_test_cases_router,
            {
                "approved": "qa_testing",
                "feedback": "revise_test_cases"
            }
        )
        self.graph_builder.add_edge("revise_test_cases", "write_test_cases")
        self.graph_builder.add_edge("qa_testing", "qa_review")
        self.graph_builder.add_conditional_edges(
            "qa_review",
            self.coding_node.review_test_cases_router,
            {
                "approved": "deployment",
                "feedback": "generate_code"
            }
        )
        self.graph_builder.add_edge("deployment", "donwload_artifacts")
        self.graph_builder.add_edge("donwload_artifacts", END)
         
        
    def setup_graph(self):
        """
        Sets up the graph
        """
        self.build_sdlc_graph()
        return self.graph_builder.compile(
            interrupt_before=[
                'get_user_requirements',
                'review_user_stories',
                'review_design_documents',
                'code_review',
                'security_review',
                'review_test_cases',
                'qa_review'
            ],checkpointer=self.memory
        )
        
             
    # def setup_graph(self):
    #     """
    #     Sets up the graph
    #     """
    #     self.build_sdlc_graph()
    #     graph =self.graph_builder.compile(
    #         interrupt_before=[
    #             'get_user_requirements',
    #             'review_user_stories',
    #             'review_design_documents',
    #             'code_review',
    #             'security_review',
    #             'review_test_cases',
    #             'qa_review'
    #         ],checkpointer=self.memory
    #     )
    #     self.save_graph_image(graph)         
    #     return graph
    
    
    def save_graph_image(self,graph):
        # Generate the PNG image
        img_data = graph.get_graph().draw_mermaid_png(
            draw_method=MermaidDrawMethod.API
            )

        # Save the image to a file
        graph_path = "workflow_graph.png"
        with open(graph_path, "wb") as f:
            f.write(img_data)        
            
        