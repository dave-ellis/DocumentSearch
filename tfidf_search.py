class TfIdfTable:
    def __init__(self):
        self.weighted = False
        self.documents = []
        self.overall_term_counts = {}

    def append_document(self, doc_name, list_of_terms):
        # Count terms in document
        doc_term_counts = {} 
        for term in list_of_terms:
            doc_term_counts[term] = doc_term_counts.get(term, 0.0) + 1.0

        # Normalise doc term counts
        length  = float(len(list_of_terms))
        doc_term_normals = {}
        for term, count in doc_term_counts.items():
            doc_term_normals[term] = count / length

        # Append overall term counts
        for term in list_of_terms:
            self.overall_term_counts[term] = self.overall_term_counts.get(term, 0.0) + 1.0

        self.documents.append([doc_name, doc_term_normals])

    def search(self, search, threshold=0.0):
        search_terms = [x.lower() for x in search.split()]

        # Count the search terms
        search_term_counts = {}
        for term in search_terms:
            search_term_counts[term] = search_term_counts.get(term, 0.0) + 1.0

        # Normalise doc term counts
        length = float(len(search_terms))
        search_term_normals = {}
        for term, count in search_term_counts.items():
            search_term_normals[term] = count / length

        print("Searching index with", len(self.overall_term_counts), "terms for", search_term_normals)

        # Calculate term scores...
        term_scores = []
        for doc in self.documents:
            score = 0.0
            doc_term_counts = doc[1]
            for term in search_term_normals:
                if term in doc_term_counts:
                    search_term_normal = search_term_normals[term]
                    doc_term_normal = doc_term_counts[term]
                    overall_term_count = self.overall_term_counts[term]

                    score += (search_term_normal + doc_term_normal) / overall_term_count

            if score > threshold:
                term_scores.append((doc[0], score))

        return  term_scores

    def __len__(self):
        return len(self.documents)
